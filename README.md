# Resin Print Portal (RPP)

A web interface for managing and monitoring Elegoo resin 3D printers over WiFi. Tested on Elegoo Mars 4 Ultra.

Fork of [RPP](https://github.com/jjtronics/RPP) by JJtronics, built on [Cassini](https://github.com/vvuk/cassini) by Vladimir Vukicevic.

## Features

- Upload `.ctb` / `.goo` files to the server
- Send files to the printer and start printing
- Real-time print progress
- Pause, Resume and Stop a running print
- Printer online/offline status
- Configure printer IP address or hostname

## Installation

Tested on Ubuntu 24.04.

**Install dependencies:**
```bash
sudo apt update
sudo apt install git python3-pip python3-flask
sudo pip3 install alive-progress --break-system-packages
```

**Clone the repository:**
```bash
cd /opt/
git clone https://github.com/MichielBruijn/RPP.git
cd RPP
```

**Set permissions:**
```bash
sudo chmod 775 /opt/RPP/uploads /opt/RPP/printer_ip.txt
sudo chown www-data:www-data /opt/RPP/uploads /opt/RPP/printer_ip.txt
```

**Optional — set printer IP now:**
```bash
echo 192.168.1.50 > printer_ip.txt
```

**Install and start the service:**
```bash
sudo mv rpp.service /etc/systemd/system/
sudo systemctl enable rpp
sudo systemctl start rpp
sudo systemctl status rpp
```

The interface runs on port **5001**. Use a reverse proxy (nginx, Apache) to expose it on port 80/443.

## Update

```bash
cd /opt/RPP/
sudo git reset --hard HEAD
sudo git pull
sudo chmod 775 /opt/RPP/uploads /opt/RPP/printer_ip.txt
sudo chown www-data:www-data /opt/RPP/uploads /opt/RPP/printer_ip.txt
sudo systemctl restart rpp
```

## Notes on pause and stop

The Elegoo SDCP protocol has three distinct paused states:

| State | Cause | How to resume |
|---|---|---|
| PAUSED_LIFTED (8) | RPP Pause button | RPP Resume button |
| PAUSED_HW (7) | Pause via printer touchscreen | RPP Resume button or printer display |
| PAUSED (14) | RPP Stop button | Print is abandoned — start a new one |

Pressing **Stop** in RPP sends a stop command and the printer ends the current print. The printer firmware briefly reports state 14 before returning to idle.

## Credits

- Original RPP by [JJtronics](https://github.com/jjtronics/RPP)
- Cassini by [Vladimir Vukicevic](https://github.com/vvuk/cassini)
- Licensed under [MIT](LICENSE)
