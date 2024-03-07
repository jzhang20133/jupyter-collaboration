from jupyter_collaboration.utils import JUPYTER_COLLABORATION_EVENTS_URI, LogLevel, decode_file_path
from jupyter_events import EventLogger
import asyncio

class LiveNotebookEventListener:
    """A Listener that should listen to event with the following schema id
        https://schema.jupyter.org/jupyter_collaboration/session/v1

    In response, it will choose whether to shut down the room
    """

    def __init__(self, serverapp, ywebsocket_server):
        self.serverapp = serverapp
        self.ywebsocket_server = ywebsocket_server
        self.serverapp.log.info("LiveNotebookEventListener is initialized, this is another version")

    async def __call__(self, logger: EventLogger, schema_id: str, data: dict) -> None:
        self.serverapp.log.info(f"live notebook collaboration data={data}")
        room_id = data["room"]
        msg = data["msg"]
        self.serverapp.log.info(f"live notebook collaboration msg={msg}, room_id={room_id}")
        if msg.startswith("Y user left"):
            #check for the room if host user is still around
            yroom = self.ywebsocket_server.rooms[room_id]
            self.serverapp.log.info(f"live notebook collaboration yroom={yroom}, clients={yroom.clients}")
            owner_exist = False
            for ydocwebsockethandler in yroom.clients:
                user = ydocwebsockethandler.current_user
                if await self.serverapp.authorizer.is_owner(user):
                    owner_exist = True
                    break
            self.serverapp.log.info(f"live notebook collaboration owner_exist={owner_exist}")
            if not owner_exist: 
                for ydocwebsockethandler in yroom.clients:
                    ydocwebsockethandler.close() # this will make user left so trigger on_close as well
                    self.serverapp.log.info(f"live notebook collaboration close ydocwebsockethandler={ydocwebsockethandler}")
                    self.emit(room_id, LogLevel.INFO, None, "Host left")
        if msg.startswith("Y user joined"):
            #check for the room if host user is still around
            yroom = self.ywebsocket_server.rooms[room_id]
            self.serverapp.log.info(f"live notebook collaboration yroom={yroom}, clients={yroom.clients}")
            owner_exist = False
            for ydocwebsockethandler in yroom.clients:
                user = ydocwebsockethandler.current_user
                if await self.serverapp.authorizer.is_owner(user):
                    owner_exist = True
                    break
            self.serverapp.log.info(f"live notebook collaboration owner_exist={owner_exist}")
            if not owner_exist: 
                self.emit(room_id, LogLevel.INFO, None, "Guest joins when host is not around")
    
    def emit(self, room_id: str, level: LogLevel, action: str | None = None, msg: str | None = None) -> None:
        _, _, file_id = decode_file_path(room_id)
        path = self.serverapp.web_app.settings["file_id_manager"].get_path(file_id)

        data = {"level": level.value, "room": room_id, "path": path}
        if action:
            data["action"] = action
        if msg:
            data["msg"] = msg

        self.serverapp.event_logger.emit(schema_id=JUPYTER_COLLABORATION_EVENTS_URI, data=data)
            
        