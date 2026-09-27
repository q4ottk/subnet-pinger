import os
import sys
import time
import signal
import platform
import subprocess
import ipaddress
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# CONFIG
# ============================================================

CONFIG_FILE = "config.txt"

DEFAULT_CONFIG = {
    "PING_TIMEOUT": 1.0,
    "THREADS": 64,
    "COLUMNS": 6,
    "SCAN_INTERVAL": 1.0,
    "MAX_IPS": 50,
}


# ============================================================
# CORES
# ============================================================

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
WHITE = "\033[97m"
GRAY = "\033[90m"
CYAN = "\033[36m"
YELLOW = "\033[33m"


# ============================================================
# CONTROLE
# ============================================================

stop_event = threading.Event()


def ignore_ctrl_c(signum, frame):
    pass


signal.signal(signal.SIGINT, ignore_ctrl_c)

if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, ignore_ctrl_c)


# ============================================================
# ESC
# ============================================================

def esc_listener():
    """
    Listener separado para ESC.

    Windows:
        usa msvcrt.

    Git Bash/Linux:
        tenta leitura direta do terminal.
    """

    system = platform.system().lower()

    # --------------------------------------------------------
    # WINDOWS
    # --------------------------------------------------------

    if system == "windows":

        try:
            import msvcrt

            while not stop_event.is_set():

                if msvcrt.kbhit():

                    key = msvcrt.getch()

                    if key == b"\x1b":
                        stop_event.set()
                        return

                time.sleep(0.02)

            return

        except Exception:
            pass

    # --------------------------------------------------------
    # UNIX / GIT BASH
    # --------------------------------------------------------

    try:

        import select
        import termios
        import tty

        fd = sys.stdin.fileno()

        old_settings = termios.tcgetattr(fd)

        try:

            tty.setcbreak(fd)

            while not stop_event.is_set():

                ready, _, _ = select.select(
                    [sys.stdin],
                    [],
                    [],
                    0.05
                )

                if ready:

                    char = sys.stdin.read(1)

                    if char == "\x1b":
                        stop_event.set()
                        return

        finally:

            termios.tcsetattr(
                fd,
                termios.TCSADRAIN,
                old_settings
            )

    except Exception:
        pass


# ============================================================
# CONFIG.TXT
# ============================================================

def load_config():

    config = DEFAULT_CONFIG.copy()

    if not os.path.exists(CONFIG_FILE):
        return config

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                line = line.strip()

                if not line:
                    continue

                if line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split(
                    "=",
                    1
                )

                key = key.strip().upper()
                value = value.strip()

                if key not in config:
                    continue

                try:

                    if key in (
                        "PING_TIMEOUT",
                        "SCAN_INTERVAL"
                    ):

                        config[key] = float(value)

                    elif key in (
                        "THREADS",
                        "COLUMNS",
                        "MAX_IPS"
                    ):

                        config[key] = int(value)

                except ValueError:

                    print(
                        f"{YELLOW}[!] "
                        f"Valor inválido: "
                        f"{key}={value}"
                        f"{RESET}"
                    )

    except Exception as e:

        print(
            f"{RED}[!] Erro lendo "
            f"{CONFIG_FILE}: {e}"
            f"{RESET}"
        )

    # --------------------------------------------------------
    # LIMITES
    # --------------------------------------------------------

    config["PING_TIMEOUT"] = max(
        0.1,
        float(config["PING_TIMEOUT"])
    )

    config["THREADS"] = max(
        1,
        int(config["THREADS"])
    )

    config["COLUMNS"] = max(
        1,
        int(config["COLUMNS"])
    )

    config["SCAN_INTERVAL"] = max(
        0,
        float(config["SCAN_INTERVAL"])
    )

    config["MAX_IPS"] = max(
        1,
        int(config["MAX_IPS"])
    )

    return config


# ============================================================
# TARGET
# ============================================================

def parse_target(value):

    # --------------------------------------------------------
    # SUBNET
    # --------------------------------------------------------

    if "/" in value:

        try:

            network = ipaddress.ip_network(
                value,
                strict=False
            )

            hosts = list(network.hosts())

            if not hosts:

                print(
                    f"{RED}[!] "
                    f"A subnet não possui hosts."
                    f"{RESET}"
                )

                sys.exit(1)

            return hosts

        except ValueError:

            print(
                f"{RED}[!] Subnet inválida: "
                f"{value}"
                f"{RESET}"
            )

            sys.exit(1)

    # --------------------------------------------------------
    # IP
    # --------------------------------------------------------

    try:

        ip = ipaddress.ip_address(
            value
        )

        return [ip]

    except ValueError:

        print(
            f"{RED}[!] IP ou subnet inválida: "
            f"{value}"
            f"{RESET}"
        )

        sys.exit(1)


# ============================================================
# PING
# ============================================================

def ping(ip, timeout):

    system = platform.system().lower()

    try:

        # ----------------------------------------------------
        # WINDOWS
        # ----------------------------------------------------

        if system == "windows":

            timeout_ms = max(
                1,
                int(timeout * 1000)
            )

            command = [
                "ping",
                "-n",
                "1",
                "-w",
                str(timeout_ms),
                str(ip)
            ]

        # ----------------------------------------------------
        # LINUX
        # ----------------------------------------------------

        else:

            timeout_seconds = max(
                1,
                int(timeout)
            )

            command = [
                "ping",
                "-c",
                "1",
                "-W",
                str(timeout_seconds),
                str(ip)
            ]

        # ----------------------------------------------------
        # TIMEOUT DE SEGURANÇA
        # ----------------------------------------------------

        process_timeout = (
            timeout + 1.0
        )

        kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "timeout": process_timeout,
        }

        if system == "windows":

            kwargs["creationflags"] = (
                subprocess.CREATE_NO_WINDOW
            )

        result = subprocess.run(
            command,
            **kwargs
        )

        return result.returncode == 0

    except subprocess.TimeoutExpired:

        return False

    except Exception:

        return False


# ============================================================
# SCAN DE IP
# ============================================================

def scan_ip(ip, timeout):

    start = time.perf_counter()

    status = ping(
        ip,
        timeout
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    return (
        str(ip),
        status,
        elapsed
    )


# ============================================================
# SCAN
# ============================================================

def scan_hosts(hosts, config):

    results = {}

    executor = ThreadPoolExecutor(
        max_workers=config["THREADS"]
    )

    futures = {}

    try:

        # ----------------------------------------------------
        # CRIA TASKS
        # ----------------------------------------------------

        for ip in hosts:

            if stop_event.is_set():
                break

            future = executor.submit(
                scan_ip,
                ip,
                config["PING_TIMEOUT"]
            )

            futures[future] = ip

        total = len(futures)
        completed = 0

        # ----------------------------------------------------
        # RECEBE CONFORME TERMINAM
        # ----------------------------------------------------

        for future in as_completed(futures):

            if stop_event.is_set():
                break

            try:

                ip, status, elapsed = (
                    future.result()
                )

                results[ip] = (
                    status,
                    elapsed
                )

            except Exception:

                ip = str(
                    futures[future]
                )

                results[ip] = (
                    False,
                    0
                )

            completed += 1

            # ------------------------------------------------
            # PROGRESSO
            # ------------------------------------------------

            if completed % 10 == 0 or completed == total:

                online = sum(
                    1
                    for status, _ in results.values()
                    if status
                )

                print(
                    f"\r"
                    f"{CYAN}Scanning "
                    f"{completed}/{total}"
                    f"{RESET}  "
                    f"ONLINE: "
                    f"{GREEN}{online}"
                    f"{RESET}",
                    end="",
                    flush=True
                )

    finally:

        # ----------------------------------------------------
        # NÃO ESPERA TASKS PENDENTES
        # ----------------------------------------------------

        for future in futures:

            if not future.done():

                future.cancel()

        executor.shutdown(
            wait=False,
            cancel_futures=True
        )

    print()

    return results


# ============================================================
# LIMPAR
# ============================================================

def clear_screen():

    print(
        "\033[2J\033[H",
        end=""
    )


# ============================================================
# TABELA
# ============================================================

def render_table(
    results,
    target,
    total_hosts,
    round_number,
    scan_time,
    started,
    config
):

    online = sum(
        1
        for status, _ in results.values()
        if status
    )

    offline = (
        len(results)
        - online
    )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    print(
        f"Time: {time.strftime('%H:%M:%S')}  "
        f"Round: #{round_number}  "
        f"Scan: {scan_time:.2f}s"
    )

    print(
        f"ONLINE: {GREEN}{online}{RESET}  "
        f"OFFLINE: {RED}{offline}{RESET}  "
        f"Total: {total_hosts}"
    )

    print(
        f"Network: {target} · "
        f"{total_hosts} hosts · "
        f"ping icmp · running"
    )

    print()

    # --------------------------------------------------------
    # CONFIG
    # --------------------------------------------------------

    print(
        f"{GRAY}"
        f"Timeout: {config['PING_TIMEOUT']}s  ·  "
        f"Threads: {config['THREADS']}  ·  "
        f"Interval: {config['SCAN_INTERVAL']}s  ·  "
        f"Max IPs: {config['MAX_IPS']}"
        f"{RESET}"
    )

    print()

    # --------------------------------------------------------
    # TABELA
    # --------------------------------------------------------

    CELL_WIDTH = 35
    columns = config["COLUMNS"]

    print(
        "╔" +
        "╤".join(
            ["═" * CELL_WIDTH] * columns
        ) +
        "╗"
    )

    headers = []

    for _ in range(columns):

        headers.append(
            f"{'IP':<15} {'STATUS':<18}"
        )

    print(
        "║" +
        "│".join(headers) +
        "║"
    )

    print(
        "╠" +
        "╪".join(
            ["═" * CELL_WIDTH] * columns
        ) +
        "╣"
    )

    # --------------------------------------------------------
    # IPS
    # --------------------------------------------------------

    ips = list(results.keys())

    rows = (
        len(ips)
        + columns
        - 1
    ) // columns

    for row in range(rows):

        cells = []

        for column in range(columns):

            index = (
                row
                + column * rows
            )

            if index < len(ips):

                ip = ips[index]

                status, elapsed = (
                    results[ip]
                )

                if status:

                    status_text = (
                        f"{GREEN}ONLINE{RESET}"
                    )

                    status_plain = "ONLINE"

                else:

                    status_text = (
                        f"{RED}OFFLINE{RESET}"
                    )

                    status_plain = "OFFLINE"

                padding = max(
                    0,
                    18 - len(status_plain)
                )

                cell = (
                    f"{ip:<15} "
                    f"{status_text}"
                    f"{' ' * padding}"
                )

                cells.append(cell)

            else:

                cells.append(
                    " " * CELL_WIDTH
                )

        print(
            "║" +
            "│".join(cells) +
            "║"
        )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print(
        "╚" +
        "╧".join(
            ["═" * CELL_WIDTH] * columns
        ) +
        "╝"
    )

    print()

    print(
        f"{GRAY}"
        f"Running for "
        f"{time.time() - started:.0f}s"
        f" · Press ESC to exit"
        f"{RESET}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # ARGUMENTO
    # --------------------------------------------------------

    if len(sys.argv) != 2:

        print(
            f"{WHITE}Uso:{RESET}"
        )

        print(
            "  python main.py <IP|CIDR>"
        )

        print()

        print(
            f"{WHITE}Exemplos:{RESET}"
        )

        print(
            "  python main.py 213.178.215.10"
        )

        print(
            "  python main.py 213.178.215.0/24"
        )

        sys.exit(1)

    target = sys.argv[1]

    # --------------------------------------------------------
    # CONFIG
    # --------------------------------------------------------

    config = load_config()

    # --------------------------------------------------------
    # TARGET
    # --------------------------------------------------------

    hosts = parse_target(
        target
    )

    # --------------------------------------------------------
    # LIMITE DE IPS
    # --------------------------------------------------------

    if len(hosts) > config["MAX_IPS"]:

        hosts = hosts[
            :config["MAX_IPS"]
        ]

    total_hosts = len(hosts)

    # --------------------------------------------------------
    # TELA INICIAL
    # --------------------------------------------------------

    clear_screen()

    print(
        f"{CYAN}Subnet Scanner{RESET}"
    )

    print(
        f"Target: {WHITE}{target}{RESET}"
    )

    print(
        f"Hosts: {WHITE}{total_hosts}{RESET}"
    )

    print(
        f"Max IPs: "
        f"{WHITE}{config['MAX_IPS']}{RESET}"
    )

    print(
        f"Timeout: "
        f"{WHITE}{config['PING_TIMEOUT']}s{RESET}"
    )

    print(
        f"Threads: "
        f"{WHITE}{config['THREADS']}{RESET}"
    )

    print()

    print(
        f"{GRAY}Press ESC to stop...{RESET}"
    )

    print()

    # --------------------------------------------------------
    # ESC
    # --------------------------------------------------------

    threading.Thread(
        target=esc_listener,
        daemon=True
    ).start()

    # --------------------------------------------------------
    # SCANNER
    # --------------------------------------------------------

    started = time.time()
    round_number = 0

    while not stop_event.is_set():

        round_number += 1

        # ----------------------------------------------------
        # SCAN
        #
        # NÃO LIMPA A TELA AQUI.
        #
        # A tabela anterior continua visível enquanto o novo
        # scan está sendo realizado.
        # ----------------------------------------------------

        scan_start = time.perf_counter()

        results = scan_hosts(
            hosts,
            config
        )

        scan_time = (
            time.perf_counter()
            - scan_start
        )

        if stop_event.is_set():
            break

        # ----------------------------------------------------
        # NOVO RESULTADO PRONTO
        #
        # SOMENTE AGORA LIMPA A TELA ANTIGA.
        # ----------------------------------------------------

        clear_screen()

        # ----------------------------------------------------
        # MOSTRA NOVO RESULTADO
        # ----------------------------------------------------

        render_table(
            results,
            target,
            total_hosts,
            round_number,
            scan_time,
            started,
            config
        )

        # ----------------------------------------------------
        # INTERVALO
        # ----------------------------------------------------

        stop_event.wait(
            config["SCAN_INTERVAL"]
        )

    # --------------------------------------------------------
    # EXIT
    # --------------------------------------------------------

    clear_screen()

    print(
        f"{CYAN}Scanner encerrado.{RESET}"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
