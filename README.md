# RESIN PRINT PORTAL (RPP)

## About RESIN PRINT PORTAL

**RESIN PRINT PORTAL (RPP)** is a web interface designed to facilitate the management and monitoring of resin-based 3D printing. Currently, only Elegoo WiFi printers are supported. Tested on Elegoo Mars 4 Ultra

This is a fork of [RPP](https://github.com/jjtronics/RPP) by JJtronics, which is based on the [Cassini](https://github.com/vvuk/cassini) project by Vladimir Vukicevic.

### Features
- File uploading for printing.
- Launching and real-time tracking of prints.

### Contribution
Contributions to this project are welcome. Feel free to create a pull request or open an issue.

### Installation (Tested on Ubuntu 24.04)

Installing dependencies:
```
sudo apt update
sudo apt install git python3-pip python3-flask
sudo pip3 install alive-progress --break-system-packages
``` 

Clone the repository: 
```
cd /opt/
git clone https://github.com/MichielBruijn/RPP.git
```

Give write permissions to the upload folder and printer IP file: 
```
sudo chmod -R 775 /opt/RPP/uploads
sudo chown -R www-data:www-data /opt/RPP/uploads
sudo chmod -R 775 /opt/RPP/printer_ip.txt
sudo chown -R www-data:www-data /opt/RPP/printer_ip.txt
```

Go to the folder: 
```
cd RPP
```

*Optional: configure your printer's IP address now*: 
```
echo 192.168.1.50 > printer_ip.txt
```

Copy the systemd script to manage automatic launch at system startup: 
```
sudo mv rpp.service /etc/systemd/system/
sudo systemctl enable rpp
sudo systemctl start rpp
```

To verify proper operation: 
```
sudo systemctl status rpp
```

The interface is accessible on port 5001. It is recommended to use a reverse proxy like nginx or Apache.

### Update 

```
cd /opt/RPP/
sudo git reset --hard HEAD
sudo git pull
```

Restore write permissions after update:
```
sudo chmod -R 775 /opt/RPP/uploads
sudo chown -R www-data:www-data /opt/RPP/uploads
sudo chmod -R 775 /opt/RPP/printer_ip.txt
sudo chown -R www-data:www-data /opt/RPP/printer_ip.txt
```

## Credits

- Original RPP project by [JJtronics](https://github.com/jjtronics/RPP)
- Cassini printer communication library by [Vladimir Vukicevic](https://github.com/vvuk/cassini)
- Licensed under [MIT](LICENSE)
