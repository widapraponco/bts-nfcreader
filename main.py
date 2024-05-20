import flet as ft
from py122u import nfc
import socketio
import eventlet
from smartcard.util import toHexString

sio = socketio.Server(async_mode='eventlet',cors_allowed_origins=[
    'http://localhost:4200',
    'https://btstrans-d4879.firebaseapp.com'
])

states = ["disconnected", "connected", "reads", "write", "payment", "clean", "newer", "none"]
stateIndex = 0
lastCardUID = ''

# reader = nfc.Reader()

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

@sio.event
def connect(sid, environ, auth):
    global stateIndex

    stateIndex = 1
    sio.emit('connected', True)
    print('connect ', sid)

@sio.on('change')
def onChange(sid, data):
    global stateIndex, lastCardUID
    lastCardUID = ''
    currentState = data.split('!')
    stateIndex = states.index(currentState[0])
    print(stateIndex)

@sio.event
def disconnect(sid):
    global stateIndex

    stateIndex = 0
    print('disconnect ', sid)

def listenSocketIO():
    app = socketio.WSGIApp(sio)
    eventlet.wsgi.server(eventlet.listen(('', 3000)), app)

def toCardUID():
    return "#"+toHexString(reader.get_uid()).replace(" ", "")

def listenSmartCcard():
    global stateIndex, reader
    lastError = 'initiate error message'

    while True:
        try:
            reader.connect()
            # write(reader, 0x01, 0x20, [0x00 for i in range(16)])
            # print(toCardUID())
            # print(stateIndex)

            if stateIndex == 2: # read 
                # reader.load_authentication_data(0x01, [0x62, 0x74, 0x73, 0x34, 0x78, 0x34])
                # reader.authentication(0x00, 0x61, 0x01)
                # print(read(reader, 0x01, 0x20))
                reader.led_control(0xED, 0x0A, 0x01, 0x01, 0x01)
                # sio.emit('message', toCardUID())

                # change back to state none
                stateIndex = -1
            elif stateIndex == 3: # write
                # reader.load_authentication_data(0x01, [0x62, 0x74, 0x73, 0x34, 0x78, 0x34])
                # reader.authentication(0x00, 0x61, 0x01)
                # write(reader, 0x01, 0x20, [0x00 for i in range(16)])
                reader.led_control(0xED, 0x0A, 0x01, 0x01, 0x01)
                # sio.emit('message', toCardUID())

                # change back to state none
                stateIndex = -1
            elif stateIndex == 4: # clean/reset
                write(reader, 0x01, 0x20, [0x00 for i in range(16)])
                # sio.emit('message', toCardUID())
            else:
                stateIndex = -1
            #     print('none')

            if lastCardUID != toCardUID() and stateIndex != 4: #not paid state
                sio.emit('message', toCardUID())
            elif stateIndex == 4:
                sio.emit('paid', toCardUID())
            # reader.reset_lights()
        except Exception as e:
            # reader.reset_lights()
            if str(e) == lastError:
                lastError = str(e)
                print(e)

        eventlet.sleep(0.5)


def main(page: ft.Page):
    global stateIndex
    
    @sio.event
    def connect(sid, environ, auth):
        global stateIndex

        stateIndex = 1
        sio.emit('connected', True)
        print('connect ', sid)

    @sio.on('change')
    def onChange(sid, data):
        global stateIndex, lastCardUID
        lastCardUID = ''
        currentState = data.split('!')
        stateIndex = states.index(currentState[0])
        print(stateIndex)

    @sio.event
    def disconnect(sid):
        global stateIndex

        stateIndex = 0
        print('disconnect ', sid)

    # socket io setup
    # listenSIO = threading.Thread(target = listenSocketIO)
    # listenSIO.daemon = True
    # listenSIO.start()

    # listening card
    # listenReader = threading.Thread(target = listenSmartCcard)
    # listenReader.daemon = True
    # listenReader.start()

    # reader.load_authentication_data(0x01, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
    # reader.authentication(0x00, 0x61, 0x01)

    def openSite(self):
        page.launch_url('http://localhost:4200')

    def getContent():
        content = [
            ft.Text('BTS4x4 NFC App'), 
            ft.FilledButton(content=ft.Text("Open"), on_click=openSite),
            ft.Text('Tekan <Open> untuk membuka aplikasi bila disconnected'),
            ft.Text('State: '+states[stateIndex])
        ]
        
        return content

    page.window_width = 500
    page.window_height = 300
    page.window_visible = True
    page.controls.append(ft.Container(
            alignment=ft.alignment.center,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=getContent()
            ),
            expand=True,
        ))
    page.update()

    def app_lifecycle_change(e: ft.AppLifecycleStateChangeEvent):
        print(page.controls)
        if e.state == ft.AppLifecycleState.RESUME:
          page.controls.pop()
          page.update()
          page.controls.append(ft.Container(
            alignment=ft.alignment.center,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=getContent()
            ),
            expand=True,
          ))
          page.update()
          print("Update UI with fresh state: "+str(stateIndex))
    
    page.on_app_lifecycle_state_change = app_lifecycle_change
    sio.start_background_task(listenSmartCcard)
    app = socketio.WSGIApp(sio)
    eventlet.wsgi.server(eventlet.listen(('', 3000)), app)


ft.app(main)
