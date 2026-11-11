#!/usr/bin/env python3
"""Recolector del Tablero de Gestión IT de OCA.

Descarga tickets, problemas, cambios y feriados desde la API REST de GLPI
y genera data.json junto a index.html. Pensado para ejecutarse por cron
(por ejemplo cada 30 minutos) en el servidor donde se publique el tablero.

Configuración por variables de entorno o argumentos:
  GLPI_URL         https://glpi.oca.com.ar
  GLPI_APP_TOKEN   App-Token del cliente API (Configuración > General > API)
  GLPI_USER_TOKEN  Token de API del usuario de lectura (Preferencias > Token de API)
  GLPI_MONTHS      Meses de historia (por defecto 13)
"""
import argparse, json, os, sys, datetime as dt
try:
    import requests
except ImportError:
    sys.exit("Falta la librería requests: pip install requests")

T_FIELDS = [2,1,14,12,3,10,15,17,16,18,155,82,159,7,8,5,83,9,62,200,30,150,154]
P_FIELDS = [2,1,12,3,15,17,16,7,8,5,141,76685,76686,76687]
C_FIELDS = [2,1,12,3,15,17,16,7,8,5]
STEP = 500

def collect(url, app_token, user_token, months=13, insecure=False, log=sys.stderr):
    class A: pass
    a = A(); a.url, a.app_token, a.user_token, a.months, a.insecure = url, app_token, user_token, months, insecure
    return _collect(a, log)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', default=os.environ.get('GLPI_URL', 'https://glpi.oca.com.ar'))
    ap.add_argument('--app-token', default=os.environ.get('GLPI_APP_TOKEN'))
    ap.add_argument('--user-token', default=os.environ.get('GLPI_USER_TOKEN'))
    ap.add_argument('--months', type=int, default=int(os.environ.get('GLPI_MONTHS', 13)))
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json'))
    ap.add_argument('--insecure', action='store_true', help='No verificar el certificado TLS')
    a = ap.parse_args()
    if not a.app_token or not a.user_token:
        sys.exit('Faltan GLPI_APP_TOKEN y/o GLPI_USER_TOKEN')
    data = _collect(a)
    tmp = a.out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, a.out)
    print(f"OK: {len(data['tickets'])} tickets, {len(data['problems'])} problemas, {len(data['changes'])} cambios → {a.out}", file=sys.stderr)

def _collect(a, log=sys.stderr):

    base = a.url.rstrip('/') + '/apirest.php'
    s = requests.Session(); s.verify = not a.insecure
    s.headers.update({'App-Token': a.app_token, 'Content-Type': 'application/json'})
    r = s.get(base + '/initSession', headers={'Authorization': 'user_token ' + a.user_token}, timeout=60)
    r.raise_for_status()
    s.headers['Session-Token'] = r.json()['session_token']
    # Ver todas las entidades a las que tiene acceso el usuario
    s.post(base + '/changeActiveEntities', json={'entities_id': 'all', 'is_recursive': True}, timeout=60)

    today = dt.date.today()
    since = (today.replace(day=1) - dt.timedelta(days=31 * (a.months - 1))).replace(day=1)
    since_s = since.strftime('%Y-%m-%d 00:00:00')

    def search(itemtype, fields, criteria):
        out, start, total = [], 0, None
        while total is None or start < total:
            params = [('range', f'{start}-{start + STEP - 1}')]
            for i, c in enumerate(criteria):
                for k, v in c.items():
                    params.append((f'criteria[{i}][{k}]', v))
            for i, f in enumerate(fields):
                params.append((f'forcedisplay[{i}]', f))
            r = s.get(f'{base}/search/{itemtype}', params=params, timeout=300)
            if r.status_code not in (200, 206):
                if r.status_code == 400 and start == 0 and 'ERROR_RANGE' in r.text:
                    break
                r.raise_for_status()
            j = r.json(); data = j.get('data') or []
            out.extend(data); total = j.get('totalcount', len(out)); start += STEP
            print(f'  {itemtype}: {len(out)}/{total}', file=log)
            if not data:
                break
        return out

    print('Descargando tickets…', file=sys.stderr)
    t_recent = search('Ticket', T_FIELDS, [{'field': 15, 'searchtype': 'morethan', 'value': since_s}])
    t_open = search('Ticket', T_FIELDS, [{'field': 12, 'searchtype': 'equals', 'value': 'notold'}])
    tickets = {str(x.get('2')): x for x in t_recent + t_open}
    print('Descargando problemas y cambios…', file=sys.stderr)
    problems = search('Problem', P_FIELDS, [{'field': 12, 'searchtype': 'equals', 'value': 'all'}])
    changes = search('Change', C_FIELDS, [{'field': 15, 'searchtype': 'morethan', 'value': since_s}])

    holidays = []
    try:
        r = s.get(base + '/Holiday', params={'range': '0-999'}, timeout=60)
        for h in r.json() if r.ok else []:
            b = dt.date.fromisoformat(h['begin_date'][:10]); e = dt.date.fromisoformat(h['end_date'][:10])
            d = b
            while d <= e:
                if h.get('is_perpetual'):
                    for y in range(since.year, today.year + 2):
                        holidays.append(d.replace(year=y).isoformat())
                else:
                    holidays.append(d.isoformat())
                d += dt.timedelta(days=1)
    except Exception as ex:
        print('No se pudieron leer los feriados:', ex, file=sys.stderr)

    s.get(base + '/killSession', timeout=30)
    return {'generated': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
            'tickets': list(tickets.values()), 'problems': problems, 'changes': changes,
            'holidays': sorted(set(holidays))}

if __name__ == '__main__':
    main()
