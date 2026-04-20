#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Cassini
#
# Copyright (C) 2023 Vladimir Vukicevic
# License: MIT
#
import os
import pprint
import socket
import sys
import time
import asyncio
import logging
import argparse
from simple_mqtt_server import SimpleMQTTServer
from simple_http_server import SimpleHTTPServer
from saturn_printer import SaturnPrinter, PrintInfoStatus, CurrentStatus, FileStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

try:
    from alive_progress import alive_bar
except ImportError:
    logging.info("Run 'pip3 install alive-progress' for better progress bars")
    class alive_bar(object):
        def __init__(self, total, title, **kwargs):
            self.total = total
            self.title = title
        def __call__(self, x):
            print(f"{int(x*self.total)}/{self.total} {self.title}\r", end="")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            print("\n")

async def create_mqtt_server():
    mqtt = SimpleMQTTServer('0.0.0.0', 0)
    await mqtt.start()
    mqtt_server_task = asyncio.create_task(mqtt.serve_forever())
    return mqtt, mqtt.port, mqtt_server_task

async def create_http_server():
    http = SimpleHTTPServer('0.0.0.0', 0)
    await http.start()
    http_server_task = asyncio.create_task(http.serve_forever())
    return http, http.port, http_server_task

def do_status(printers):
    for i, p in enumerate(printers):
        attrs = p.desc['Data']['Attributes']
        status = p.desc['Data']['Status']
        print_info = status['PrintInfo']
        file_info = status['FileTransferInfo']
        print(f"{p.addr[0]}:")
        print(f"    {attrs['Name']} ({attrs['MachineName']})")
        print(f"    Machine Status: {CurrentStatus(status['CurrentStatus']).name}")
        print(f"    Print Status: {PrintInfoStatus(print_info['Status']).name}")
        print(f"    Layers: {print_info['CurrentLayer']}/{print_info['TotalLayer']}")
        print(f"    File: {print_info['Filename']}")
        print(f"    File Transfer Status: {FileStatus(file_info['Status']).name}")

def do_status_full(printers):
    for i, p in enumerate(printers):
        pprint.pprint(p.desc)

def do_watch(printer, interval=5, broadcast=None):
    status = printer.status()
    with alive_bar(total=status['totalLayers'], manual=True, elapsed=False, title=status['filename']) as bar:
        while True:
            printers = SaturnPrinter.find_printers(broadcast=broadcast)
            if len(printers) > 0:
                status = printers[0].status()
                pct = status['currentLayer'] / status['totalLayers']
                bar(pct)
                if pct >= 1.0:
                    break
            time.sleep(interval)

async def create_servers():
    mqtt, mqtt_port, mqtt_task = await create_mqtt_server()
    http, http_port, http_task = await create_http_server()
    return mqtt, http

async def do_print_control(printer, action_fn, action_name):
    for attempt in range(3):
        try:
            mqtt, http = await create_servers()
            printer.timeout = 8
            connected = await printer.connect(mqtt, http)
            if not connected:
                logging.error("Failed to connect to printer")
                sys.exit(1)
            ok = await action_fn(printer)
            if ok:
                logging.info(f"Print {action_name}")
                return
            else:
                logging.error(f"{action_name.capitalize()} command rejected by printer (wrong state?)")
                sys.exit(1)
        except asyncio.TimeoutError:
            if attempt < 2:
                logging.warning(f"Connection timeout, retrying ({attempt+1}/3)...")
                await asyncio.sleep(3)
            else:
                logging.error("Failed to connect to printer after 3 attempts")
                sys.exit(1)

async def do_stop(printer):
    await do_print_control(printer, lambda p: p.stop_print(), "stopped")

async def do_pause(printer):
    await do_print_control(printer, lambda p: p.pause_print(), "paused")

async def do_resume(printer):
    await do_print_control(printer, lambda p: p.resume_print(), "resumed")

async def do_print(printer, filename):
    mqtt, http = await create_servers()
    connected = await printer.connect(mqtt, http)
    if not connected:
        logging.error("Failed to connect to printer")
        sys.exit(1)

    result = await printer.print_file(filename)
    if result:
        logging.info("Print started")
    else:
        logging.error("Failed to start print")
        sys.exit(1)

async def do_upload(printer, filename, start_printing=False):
    if not os.path.exists(filename):
        logging.error(f"{filename} does not exist")
        sys.exit(1)

    mqtt, http = await create_servers()
    connected = await printer.connect(mqtt, http)
    if not connected:
        logging.error("Failed to connect to printer")
        sys.exit(1)

    upload_task = asyncio.create_task(printer.upload_file(filename, start_printing=start_printing))
    basename = filename.split('\\')[-1].split('/')[-1]
    file_size = os.path.getsize(filename)
    with alive_bar(total=file_size, manual=True, elapsed=False, title=basename) as bar:
        while True:
            if printer.file_transfer_future is None:
                await asyncio.sleep(0.1)
                continue
            progress = await printer.file_transfer_future
            if progress[0] < 0:
                logging.error("File upload failed!")
                sys.exit(1)
            bar(progress[0] / progress[1])
            if progress[0] >= progress[1]:
                break
    await upload_task

def main():
    parser = argparse.ArgumentParser(prog='cassini', description='ELEGOO Saturn printer control utility')
    parser.add_argument('-p', '--printer', help='IP address of printer to target')
    parser.add_argument('--broadcast', help='Explicit broadcast IP address')
    parser.add_argument('--debug', help='Enable debug logging', action='store_true')

    subparsers = parser.add_subparsers(title="commands", dest="command", required=True)

    subparsers.add_parser('status', help='Discover and display status of all printers')
    subparsers.add_parser('status-full', help='Discover and display full raw status of all printers')

    parser_watch = subparsers.add_parser('watch', help='Continuously update the status of the selected printer')
    parser_watch.add_argument('--interval', type=int, help='Status update interval (seconds)', default=5)

    parser_upload = subparsers.add_parser('upload', help='Upload a file to the printer')
    parser_upload.add_argument('--start-printing', help='Start printing after upload is complete', action='store_true')
    parser_upload.add_argument('filename', help='File to upload')

    parser_print = subparsers.add_parser('print', help='Start printing a file already present on the printer')
    parser_print.add_argument('filename', help='File to print')

    subparsers.add_parser('stop', help='Stop the current print')
    subparsers.add_parser('pause', help='Pause the current print')
    subparsers.add_parser('resume', help='Resume a paused print')

    parser_connect_mqtt = subparsers.add_parser('connect-mqtt', help='Connect printer to particular MQTT server')
    parser_connect_mqtt.add_argument('address', help='MQTT host and port, e.g. "192.168.1.33:1883" or "mqtt.local:1883"')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    printers = []
    printer = None
    broadcast = args.broadcast
    if args.printer:
        printer = SaturnPrinter.find_printer(args.printer)
        if printer is None:
            logging.error(f"No response from printer {args.printer}")
            sys.exit(1)
        printers = [printer]
    else:
        printers = SaturnPrinter.find_printers(broadcast=broadcast)
        if len(printers) == 0:
            logging.error("No printers found on network")
            sys.exit(1)
        printer = printers[0]

    if args.command == "status":
        do_status(printers)
        sys.exit(0)

    if args.command == "status-full":
        do_status_full(printers)
        sys.exit(0)

    if args.command == "connect-mqtt":
        mqtt_host, mqtt_port = args.address.split(':')
        try:
            mqtt_host = socket.gethostbyname(mqtt_host)
        except socket.gaierror:
            pass
        for p in printers:
            p.connect_mqtt(mqtt_host, mqtt_port)

    if args.command == "watch":
        do_watch(printer, interval=args.interval, broadcast=broadcast)
        sys.exit(0)

    if args.command == "stop":
        asyncio.run(do_stop(printer))
        sys.exit(0)
    elif args.command == "pause":
        asyncio.run(do_pause(printer))
        sys.exit(0)
    elif args.command == "resume":
        asyncio.run(do_resume(printer))
        sys.exit(0)

    logging.info(f'Printer: {printer.describe()} ({printer.addr[0]})')
    if printer.busy:
        logging.error(f'Printer is busy (status: {printer.current_status})')
        sys.exit(1)

    if args.command == "upload":
        asyncio.run(do_upload(printer, args.filename, start_printing=args.start_printing))
    elif args.command == "print":
        asyncio.run(do_print(printer, args.filename))

main()