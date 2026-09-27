# Subnet Pinger

A lightweight Python subnet/IP ping monitor with configurable timeout, threads, columns, scan interval, and maximum number of IPs tested per round.

![Subnet Pinger](https://github.com/q4ottk/subnet-pinger/blob/main/image.png?raw=true)

---

## Features

* IPv4 address support
* CIDR subnet support
* Continuous scanning
* Configurable number of IPs tested
* Configurable ping timeout
* Configurable worker threads
* Configurable table columns
* Configurable interval between scans
* Real-time scan progress
* Colored terminal output
* `ESC` to stop the scanner
* `Ctrl+C` ignored
* No external Python packages required
* Works with Windows and Linux/Git Bash

---

## Requirements

You need:

* Python 3.8 or newer
* `ping` available in the operating system
* A terminal capable of displaying ANSI escape sequences

The project uses only Python standard-library modules, so there is no `pip install` step.

---

## Files

The project can be structured like this:

```text
subnet-pinger/
├── main.py
├── config.txt
├── README.md
└── image.png
```

---

# Usage

The scanner accepts either a single IPv4 address or a CIDR subnet.

## Single IP

```bash
python main.py 192.168.1.1
```

This tests only the specified IP.

---

## CIDR subnet

```bash
python main.py 192.168.1.0/24
```

For a `/24`, the scanner obtains the usable hosts from the subnet and then applies the `MAX_IPS` limit from `config.txt`.

For example:

```bash
python main.py 213.178.215.0/24
```

---

# Configuration

The scanner reads its settings from:

```text
config.txt
```

If the file does not exist, the program uses its built-in default values.

The recommended/default configuration is:

```ini
PING_TIMEOUT=1
THREADS=150
COLUMNS=5
SCAN_INTERVAL=0.05
MAX_IPS=254
```

---

# config.txt

Create a file named:

```text
config.txt
```

in the same directory as `main.py`.

Put the following inside it:

```ini
PING_TIMEOUT=1
THREADS=150
COLUMNS=5
SCAN_INTERVAL=0.05
MAX_IPS=254
```

The program reads this file every time it starts.

---

## PING_TIMEOUT

```ini
PING_TIMEOUT=1
```

Defines how long the scanner waits for a ping response.

The value is specified in seconds.

### Example

```ini
PING_TIMEOUT=1
```

Waits approximately 1 second for the ping.

A lower value:

```ini
PING_TIMEOUT=0.5
```

makes scans faster, but hosts with higher latency may be classified as offline.

A higher value:

```ini
PING_TIMEOUT=2
```

allows more time for slower hosts to respond, but increases the possible scan duration.

---

## THREADS

```ini
THREADS=150
```

Defines how many ping operations can be processed concurrently.

The default configuration uses:

```ini
THREADS=150
```

Higher values can make a large scan complete faster, but also increase the amount of concurrent work performed by the machine and network.

Example:

```ini
THREADS=50
```

or:

```ini
THREADS=150
```

---

## COLUMNS

```ini
COLUMNS=5
```

Defines how many columns are displayed in the results table.

Example:

```ini
COLUMNS=5
```

produces a table with five IP/status columns.

You can change it to:

```ini
COLUMNS=3
```

or:

```ini
COLUMNS=6
```

depending on the terminal width.

This setting only affects the visual layout of the output. It does not change how many IPs are scanned.

---

## SCAN_INTERVAL

```ini
SCAN_INTERVAL=0.05
```

Defines the delay between completed scan rounds.

The default is:

```ini
SCAN_INTERVAL=0.05
```

which means approximately 0.05 seconds between rounds.

For a slower refresh:

```ini
SCAN_INTERVAL=1
```

For example:

```ini
SCAN_INTERVAL=5
```

will wait approximately five seconds before starting the next round.

---

## MAX_IPS

```ini
MAX_IPS=254
```

Defines the maximum number of IP addresses tested in each scan round.

This is particularly useful when passing a large CIDR range.

For example:

```ini
MAX_IPS=50
```

and:

```bash
python main.py 192.168.1.0/24
```

will limit the scan to the first 50 usable hosts returned from that subnet.

With:

```ini
MAX_IPS=254
```

a typical `/24` IPv4 subnet can scan all 254 usable host addresses.

This setting does not change the CIDR itself. It only limits how many hosts from the parsed target are tested.

---

# Recommended Configuration

For the standard configuration:

```ini
PING_TIMEOUT=1
THREADS=150
COLUMNS=5
SCAN_INTERVAL=0.05
MAX_IPS=254
```

The meaning is:

| Setting         |  Value | Description                       |
| --------------- | -----: | --------------------------------- |
| `PING_TIMEOUT`  |    `1` | Up to 1 second waiting for a ping |
| `THREADS`       |  `150` | Up to 150 concurrent scan workers |
| `COLUMNS`       |    `5` | Five table columns                |
| `SCAN_INTERVAL` | `0.05` | 0.05 seconds between rounds       |
| `MAX_IPS`       |  `254` | Maximum of 254 IPs per round      |

---

# Running the Scanner

After creating `config.txt`, run:

```bash
python main.py 192.168.1.0/24
```

Or:

```bash
python main.py 213.178.215.0/24
```

For a single address:

```bash
python main.py 192.168.1.100
```

---

# Output

The scanner continuously displays information similar to:

```text
Time: 12:30:15  Round: #12  Scan: 0.87s
ONLINE: 12  OFFLINE: 242  Total: 254
Network: 192.168.1.0/24 · 254 hosts · ping icmp · running

Timeout: 1.0s  ·  Threads: 150  ·  Interval: 0.05s  ·  Max IPs: 254

╔═══════════════════════════════════╤═══════════════════════════════════╗
║IP              STATUS             │IP              STATUS             ║
╠═══════════════════════════════════╪═══════════════════════════════════╣
║192.168.1.1     ONLINE             │192.168.1.2     OFFLINE            ║
║192.168.1.3     OFFLINE            │192.168.1.4     ONLINE             ║
╚═══════════════════════════════════╧═══════════════════════════════════╝

Running for 12s · Press ESC to exit
```

The previous results remain visible while the next scan is running.

Once the new scan finishes, the old output is cleared and replaced with the new results.

---

# Stopping the Scanner

Press:

```text
ESC
```

to stop the scanner.

`Ctrl+C` is intentionally ignored.

After pressing `ESC`, the scanner exits and displays:

```text
Scanner encerrado.
```

---

# Changing the Configuration

You do not need to modify `main.py` to change the scanner settings.

Simply edit:

```text
config.txt
```

For example:

```ini
PING_TIMEOUT=2
THREADS=100
COLUMNS=4
SCAN_INTERVAL=1
MAX_IPS=100
```

Then restart the program:

```bash
python main.py 192.168.1.0/24
```

The new values will be loaded automatically.

---

# Configuration Examples

## Faster refresh

```ini
PING_TIMEOUT=0.5
THREADS=150
COLUMNS=5
SCAN_INTERVAL=0.05
MAX_IPS=254
```

---

## More conservative scanning

```ini
PING_TIMEOUT=2
THREADS=50
COLUMNS=5
SCAN_INTERVAL=1
MAX_IPS=254
```

---

## Test only 25 IPs

```ini
PING_TIMEOUT=1
THREADS=25
COLUMNS=5
SCAN_INTERVAL=0.5
MAX_IPS=25
```

Then:

```bash
python main.py 192.168.1.0/24
```

Only 25 hosts will be tested per round.

---

# Important Notes

The scanner determines whether a host is online based on the result of an ICMP ping.

A host that does not respond to ICMP can therefore appear as `OFFLINE` even when the host is otherwise reachable. Firewalls, network ACLs, and host configuration can block or filter ICMP traffic.

For this reason, `OFFLINE` should be interpreted as:

```text
No ICMP response received within the configured timeout.
```

rather than as definitive proof that the machine is powered off.

---

# CIDR Examples

Some examples:

```bash
python main.py 192.168.1.0/24
```

```bash
python main.py 10.0.0.0/24
```

```bash
python main.py 172.16.0.0/24
```

```bash
python main.py 192.168.10.0/28
```

You can also provide a single IP:

```bash
python main.py 192.168.1.1
```

---

# Summary

Minimal setup:

### 1. Create `config.txt`

```ini
PING_TIMEOUT=1
THREADS=150
COLUMNS=5
SCAN_INTERVAL=0.05
MAX_IPS=254
```

### 2. Run the scanner

```bash
python main.py 192.168.1.0/24
```

### 3. Let it continuously monitor the hosts

### 4. Press `ESC` to exit

---

## License

Use this project only on networks and systems you own or are authorized to test.
