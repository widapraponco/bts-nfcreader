import flet as ft
from py122u import nfc
import socketio
import eventlet
from smartcard.util import toHexString
from escpos.printer import Usb
from time import strftime
import asyncio
import os

VALID_TOKENS = {"klepontech123123!"}
task_running = False
running = True  # Flag to control the loop
reader = None

def is_nfc_reader_connected():
    global reader
    try: 
        if reader:
            return True
        else:
            reader = nfc.Reader()
            return reader is not None
    except:
        return False

def is_ecspos_connected():
    try:
        p = Usb(0x04b8, 0x0202)
        p.text('ESCS POS Works!')
        return True  # Printer successfully connected
    except:
        return False  # Printer not connected
    finally:
        if p:
            try:
                p.close()  # Close only if it was initialized
            except:
                pass  # Ignore any errors while closing

sio = socketio.Server(async_mode='eventlet',cors_allowed_origins='*')
#                       [
#     'http://127.0.0.1:4200',
#     'https://btstrans-d4879.firebaseapp.com',
#     'https://bts-dev.web.app'
# ])

states = ["disconnected", "connected", "reads", "write", "payment", "clean", "newer", "none"]
stateIndex = 0
lastCardUID = ''    

def write(r, position, number, data):
    while number >= 16:
        write_16(r, position, 16, data)
        number -= 16
        position += 1


def write_16(r, position, number, data):
    r.update_binary_blocks(position, number, data)


def read(r, position, number):
    result = []
    while number >= 16:
        result.append(read_16(r, position, 16))
        number -= 16
        position += 1
    return result


def read_16(r, position, number):
    return r.read_binary_blocks(position, number)

# write(reader, 0x01, 0x20, [0x00 for i in range(16)])
# print(read(reader, 0x01, 0x20))

def listenSocketIO():
    app = socketio.WSGIApp(sio)
    eventlet.wsgi.server(eventlet.listen(('', 3000)), app)

def toCardUID(r):
    return "#"+toHexString(r.get_uid()).replace(" ", "")

def listenSmartCard():
    global stateIndex, running, reader, lastCardUID
    lastError = 'initiate error message'
    
    while running:
        try:
            reader.connect()
            # write(reader, 0x01, 0x20, [0x00 for i in range(16)])
            # print(toCardUID(r))
            # print(stateIndex)

            # if stateIndex == 2: # read 
            #     # reader.load_authentication_data(0x01, [0x62, 0x74, 0x73, 0x34, 0x78, 0x34])
            #     # reader.authentication(0x00, 0x61, 0x01)
            #     # print(read(reader, 0x01, 0x20))
            #     reader.led_control(0xED, 0x0A, 0x01, 0x01, 0x01)
            #     # sio.emit('message', toCardUID(r))

            #     # change back to state none
            #     stateIndex = -1
            # elif stateIndex == 3: # write
            #     # reader.load_authentication_data(0x01, [0x62, 0x74, 0x73, 0x34, 0x78, 0x34])
            #     # reader.authentication(0x00, 0x61, 0x01)
            #     # write(reader, 0x01, 0x20, [0x00 for i in range(16)])
            #     reader.led_control(0xED, 0x0A, 0x01, 0x01, 0x01)
            #     # sio.emit('message', toCardUID(r))

            #     # change back to state none
            #     stateIndex = -1
            # elif stateIndex == 4: # payment
            #     write(reader, 0x01, 0x20, [0x00 for i in range(16)])
            #     # sio.emit('message', toCardUID(r))
            # else:
            #     stateIndex = -1
            #     print('none')
            cardUID = toCardUID(reader)
            print(cardUID)
            if lastCardUID != cardUID :
                if stateIndex != 4: #not paid state
                    sio.emit('message', cardUID)
                    lastCardUID = cardUID
                elif stateIndex == 4:
                    sio.emit('paid', cardUID)
                    lastCardUID = cardUID
            else:
                print('uid same: '+cardUID)
            # reader.reset_lights()
        except Exception as e:
            # reader.reset_lights()
            lastCardUID = ''
            print(str(e))
            if str(e) == lastError:
                lastError = str(e)
        # finally:
        #     try:
        #         reader.disconnect()  # Ensure proper disconnection
        #     except:
        #         pass  # Ignore disconnect errors

        eventlet.sleep(0.5)


def main(page: ft.Page):
    global stateIndex
    
    @sio.event
    def connect(sid, environ):
        global stateIndex, running

        running = True

        query_string = environ.get('QUERY_STRING', '')
        token = None

        if 'token=' in query_string:
            token = query_string.split('token=')[-1].split('&')[0]  # Extract token

        if token not in VALID_TOKENS:
            print(f"Unauthorized connection attempt with token: {token}")
            change_app_text_stat(False)
            return False  # Reject connection

        stateIndex = 1
        sio.emit('connected', True)

        state_text.value = "State: connected"

        updateMessage('connected!')

        change_app_text_stat(True)
        print('connect ', sid)

    @sio.on('change')
    def onChange(sid, data):
        global stateIndex, lastCardUID
        lastCardUID = ''
        currentState = data.split('!')
        stateIndex = states.index(currentState[0])

        updateMessage(states[stateIndex]+' ready!')
        print(stateIndex)

    @sio.on('haspaid')
    def hasPaid(sid, data):

        try:
            p = Usb(0x04b8,0x0202)
            p.text('BTSTrans 4x4')
            p.text('\nNama: '+data.name)
            p.text('\nKTA: '+data.kta)
            p.text('\nTanggal: '+strftime("%Y-%m-%d %H:%M:%S"))
            p.text('\nSaldo Awal: '+data.saldoAwal)
            p.text('\nBiaya: '+data.cost)
            p.text('\nSaldo Akhir: '+data.saldo)
            p.text('\nTerima Kasih')
            p.cut()
        finally:
            updateMessage('info: '+data+'\n\nprint out success!')
            p.close()

    @sio.event
    def disconnect(sid):
        global stateIndex, running

        stateIndex = 0
        running = False  # Stop the NFC loop

        state_text.value = 'State: disconnected'

        updateMessage('disconected!')
        print('disconnect ', sid)

    def updateMessage(text):
        message_text.value = text
        page.update()

    # socket io setup
    # listenSIO = threading.Thread(target = listenSocketIO)
    # listenSIO.daemon = True
    # listenSIO.start()

    # listening card
    # listenReader = threading.Thread(target = listenSmartCard)
    # listenReader.daemon = True
    # listenReader.start()

    # reader.load_authentication_data(0x01, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
    # reader.authentication(0x00, 0x61, 0x01)

    def openSite(self):
        page.launch_url('https://bts-dev.web.app')

    def change_app_text_stat(isConnected) :
        status_app_text.value = "🌐 ✅" if isConnected else "🌐 ❌"
        page.update()

    def check_nfc_status():
        global task_running
        if task_running:
            return False  # Already running, no need to start another

        try:
            if is_nfc_reader_connected() is None:
                return False
            
            task_running = True
            sio.start_background_task(listenSmartCard)
            status_nfc_text.value = "NFC ✅"
            status_nfc_text.color = "white"
            connected = True
        except Exception:
            status_nfc_text.value = "NFC ❌"
            status_nfc_text.color = "red"
            connected = False
        page.update()
        return connected

    def check_ecspos_status():
        global p
        connected = False

        try:
            p = Usb(0x04b8,0x0202)
            p.text("Hello, ESC/POS!\n")
            p.cut()
            status_ecspos_text.value = "🖨️ ✅"
            status_ecspos_text.color = "white"
            connected = True
        except Exception:
            status_ecspos_text.value = "🖨️ ❌"
            status_ecspos_text.color = "red"
            connected = False
        page.update()    
        return connected

    async def reconnect(e):
        e.control.content.value = "Reconnecting..."
        e.control.update()

        await asyncio.sleep(3)
        e.control.content.value = "Find NFC Reader..."
        e.control.update()
        await asyncio.sleep(2)
        if not is_nfc_reader_connected() and not check_nfc_status():
            e.control.content.value = "NFC Reader Not Found"
            e.control.update()
        else:
            e.control.content.value = "NFC Reader Found"
            e.control.update()

        await asyncio.sleep(2)

        e.control.content.value = "Find ESCPOS..."
        e.control.update()

        await asyncio.sleep(2)
        if not is_ecspos_connected() and not check_ecspos_status():
            e.control.content.value = "ECSPOS Not Found"
            e.control.update()
        else:
            e.control.content.value = "ECSPOS Found"
            e.control.update()

        await asyncio.sleep(2)
        if not is_nfc_reader_connected() or not is_ecspos_connected():
            e.control.content.value = "Reconnect"
            e.control.update()
        else:
            e.control.content.value = "Connected"
            e.control.update()

        page.update()

    message_text = ft.Text('', size=10, color="white", weight=ft.FontWeight.W_200)
    state_text = ft.Text('State: '+states[stateIndex])
    status_app_text = ft.Text("🌐 ✅" if stateIndex > 0 else "🌐 ❌", size=12, color="white")
    status_ecspos_text = ft.Text("🖨️ ✅" if is_ecspos_connected() else "🖨️ ❌", size=12, color="white")
    status_nfc_text = ft.Text("NFC ✅" if is_nfc_reader_connected() else "NFC ❌", size=12, color="white")

    page.window.width = 480
    page.window.height = 300
    page.window.visible = True
    page.window.resizable = False
    icon_path = os.path.abspath("assets/bts.ico")  # Absolute path
    page.window.icon = icon_path  # Set the icon

    # page.controls.append(ft.Container(
    #         alignment=ft.alignment.center,
    #         content=ft.Column(
    #             alignment=ft.MainAxisAlignment.CENTER,
    #             horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    #             controls=[
    #                 ft.Text('BTS4x4 NFC App', weight=ft.FontWeight.BOLD), 
    #                 # ft.FilledButton(content=ft.Text("Reconnect"), on_click=lambda e: page.run_task(reconnect, e)),
    #                 ft.Text('Pastikan semua status ✅ dan tidak ❌ untuk memulai, tekan reconnect untuk merubah status, bila masih ada yg tidak terkoneksi pastikan internet dan kabel usb terhubung', size=10, weight=ft.FontWeight.W_100, color="white", text_align=ft.TextAlign.CENTER),
    #                 state_text
    #             ]
    #         ),
    #         expand=True,
    #     ))

    page.add(
        ft.Container(
            alignment=ft.alignment.center,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text('BTS4x4 NFC App', weight=ft.FontWeight.BOLD), 
                    ft.FilledButton(content=ft.Text("Reconnect"), on_click=lambda e: page.run_task(reconnect, e)),
                    ft.Text('Pastikan semua status ✅ dan tidak ❌ untuk memulai, tekan reconnect untuk merubah status, bila masih ada yg tidak terkoneksi pastikan internet dan kabel usb terhubung', size=10, weight=ft.FontWeight.W_100, color="white", text_align=ft.TextAlign.CENTER),
                    state_text,
                    ft.Container(
                        padding=ft.padding.all(4),
                        alignment=ft.alignment.center,
                        bgcolor='#6a6a6a',
                        expand=True,
                        content=ft.Column(
                            spacing=2,
                            alignment=ft.MainAxisAlignment.START,
                            horizontal_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Container(
                                    alignment=ft.alignment.center_left,
                                    content=ft.Text('Console Log:', color='#9e9e9e', text_align=ft.TextAlign.LEFT, size=10, weight=ft.FontWeight.W_100)
                                ),
                                ft.Container(
                                    alignment=ft.alignment.center_left,
                                    content=message_text
                                )
                        ])
                    )
                ]
            ),
            expand=True,
        ),
        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            status_app_text,
            status_nfc_text,
            status_ecspos_text
        ]),
    )

    page.update()

    # check nfc reader connect run as background task
    check_nfc_status()
    check_ecspos_status()

    app = socketio.WSGIApp(sio)
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 3000)), app)


ft.app(target=main, view=ft.FLET_APP)
