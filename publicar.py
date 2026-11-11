#!/usr/bin/env python3
"""Publica el Tablero de Gestión IT de OCA en GitHub Pages.

Corre DENTRO de la red de OCA (GLPI no es accesible desde internet):
  1. Descarga tickets, problemas y cambios de la API de GLPI (collector.py).
  2. Comprime y cifra los datos con la contraseña del tablero (AES-256-GCM, PBKDF2).
  3. Sube data.enc al repositorio de GitHub; GitHub Pages lo publica.

La configuración se lee de publicar.env (junto a este archivo) o de variables de entorno:
  GLPI_URL, GLPI_APP_TOKEN, GLPI_USER_TOKEN, GLPI_MONTHS
  TABLERO_PASSWORD   contraseña que se comparte con quienes ven el tablero
  GITHUB_TOKEN       token fine-grained con permiso Contents: Read and write sobre el repo
  GITHUB_REPO        usuario/repositorio, p. ej. fvergara/tablero-it-oca
Requiere: pip install requests cryptography
"""
import base64, gzip, json, os, sys, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import requests
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except ImportError:
    sys.exit('Faltan librerías: pip install requests cryptography')
from collector import collect

ITER = 310000

def load_env():
    p = os.path.join(HERE, 'publicar.env')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

def need(k):
    v = os.environ.get(k)
    if not v:
        sys.exit(f'Falta {k} en publicar.env')
    return v

def encrypt(data, password):
    raw = gzip.compress(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(password.encode('utf-8'))
    ct = AESGCM(key).encrypt(iv, raw, None)
    e = lambda b: base64.b64encode(b).decode()
    return {'v': 1, 'iter': ITER, 'salt': e(salt), 'iv': e(iv), 'ct': e(ct)}

def upload(repo, token, path, content_bytes, message):
    api = f'https://api.github.com/repos/{repo}/contents/{path}'
    h = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    r = requests.get(api, headers=h, timeout=60)
    sha = r.json().get('sha') if r.status_code == 200 else None
    body = {'message': message, 'content': base64.b64encode(content_bytes).decode()}
    if sha:
        body['sha'] = sha
    r = requests.put(api, headers=h, json=body, timeout=120)
    if r.status_code not in (200, 201):
        sys.exit(f'GitHub rechazó la subida ({r.status_code}): {r.text[:300]}')

def main():
    load_env()
    password = need('TABLERO_PASSWORD')
    if len(password) < 12:
        sys.exit('La contraseña del tablero debe tener al menos 12 caracteres.')
    data = collect(need('GLPI_URL'), need('GLPI_APP_TOKEN'), need('GLPI_USER_TOKEN'),
                   int(os.environ.get('GLPI_MONTHS', 13)))
    enc = json.dumps(encrypt(data, password)).encode()
    upload(need('GITHUB_REPO'), need('GITHUB_TOKEN'), 'data.enc', enc,
           'Datos del tablero ' + dt.datetime.now().strftime('%Y-%m-%d %H:%M'))
    print(f"Publicado: {len(data['tickets'])} tickets, {len(data['problems'])} problemas, {len(data['changes'])} cambios ({len(enc)//1024} KB)")

if __name__ == '__main__':
    main()
