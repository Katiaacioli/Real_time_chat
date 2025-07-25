import asyncio
import time
from datetime import datetime
from typing import Dict, List

import redis.asyncio as redis
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Log, Select


class ChatRedisClient:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.channels: Dict[str, str] = {}
        
    async def create_channel(self, channel_name: str) -> bool:
        stream_key = f"chat:{channel_name}"
        try:
            await self.redis.xadd(
                stream_key,
                {"type": "system", "message": f"Canal {channel_name} criado", "timestamp": time.time()}
            )
            self.channels[channel_name] = stream_key
            return True
        except Exception as e:
            print(f"Erro ao criar canal {channel_name}: {e}")
            return False
    
    async def send_message(self, channel_name: str, username: str, message: str) -> bool:
        if channel_name not in self.channels:
            return False
            
        stream_key = self.channels[channel_name]
        try:
            await self.redis.xadd(stream_key, {
                "type": "message",
                "username": username,
                "message": message,
                "timestamp": time.time()
            })
            return True
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            return False
    
    async def get_messages(self, channel_name: str, last_id: str = "0") -> List[Dict]:
        if channel_name not in self.channels:
            return []
            
        stream_key = self.channels[channel_name]
        try:
            messages = await self.redis.xread({stream_key: last_id}, count=100, block=0)
            result = []
            for stream, msgs in messages:
                for msg_id, fields in msgs:
                    result.append({
                        "id": msg_id,
                        "type": fields.get("type", "message"),
                        "username": fields.get("username", "Sistema"),
                        "message": fields.get("message", ""),
                        "timestamp": float(fields.get("timestamp", time.time()))
                    })
            return result
        except Exception as e:
            print(f"Erro ao recuperar mensagens: {e}")
            return []
    
    async def listen_for_messages(self, channel_name: str, last_id: str = "$"):
        if channel_name not in self.channels:
            return
            
        stream_key = self.channels[channel_name]
        current_id = last_id
        
        while True:
            try:
                messages = await self.redis.xread({stream_key: current_id}, count=1, block=1000)
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        current_id = msg_id
                        yield {
                            "id": msg_id,
                            "type": fields.get("type", "message"),
                            "username": fields.get("username", "Sistema"),
                            "message": fields.get("message", ""),
                            "timestamp": float(fields.get("timestamp", time.time()))
                        }
            except Exception as e:
                print(f"Erro ao escutar mensagens: {e}")
                await asyncio.sleep(1)
    
    async def get_channels(self) -> List[str]:
        try:
            keys = await self.redis.keys("chat:*")
            channels = [key.replace("chat:", "") for key in keys]
            for channel in channels:
                if channel not in self.channels:
                    self.channels[channel] = f"chat:{channel}"
            return channels
        except Exception as e:
            print(f"Erro ao buscar canais: {e}")
            return []
    
    async def close(self):
        await self.redis.aclose()


class ChatApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    
    .sidebar {
        dock: left;
        width: 35;
        background: $panel;
        border-right: solid $primary;
    }
    
    .main-content {
        width: 1fr;
        background: $surface;
    }
    
    .chat-area {
        height: 1fr;
        margin: 1;
    }
    
    .input-area {
        dock: bottom;
        height: 4;
        background: $panel;
        border-top: solid $primary;
    }
    
    .channel-section {
        height: 50%;
        margin: 1;
        border: solid $primary;
    }
    
    .user-section {
        height: 50%;
        margin: 1;
        border: solid $accent;
    }
    
    .channel-list {
        height: 1fr;
        margin: 1;
    }
    
    .user-controls {
        height: 1fr;
        margin: 1;
    }
    
    .section-title {
        text-align: center;
        background: $primary;
        color: $text;
        padding: 0 1;
        margin-bottom: 1;
    }
    
    .user-section .section-title {
        background: $accent;
    }
    
    Log {
        border: solid $primary;
        padding: 1;
    }
    
    Input {
        margin: 1;
    }
    
    Button {
        margin: 1;
        min-width: 12;
    }
    
    .send-area {
        layout: horizontal;
    }
    
    .message-input {
        width: 1fr;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Sair"),
        ("r", "refresh_channels", "Atualizar Canais"),
    ]
    
    def __init__(self):
        super().__init__()
        self.redis_client = ChatRedisClient()
        self.current_channel = None
        self.username = "Usuario"
        self.last_message_id = "0"
        
    async def on_mount(self) -> None:
        await self.redis_client.create_channel("geral")
        await self.redis_client.create_channel("random")
        await self.refresh_channels()
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal():
            with Vertical(classes="sidebar"):
                with Vertical(classes="channel-section"):
                    yield Label("CANAIS DISPONÍVEIS", classes="section-title")
                    yield Select([], id="channel-select", classes="channel-list")
                    yield Input(placeholder="Nome do novo canal", id="new-channel-input")
                    yield Button("Criar Canal", id="create-channel-btn", variant="success")
                
                with Vertical(classes="user-section"):
                    yield Label("SEU PERFIL", classes="section-title")
                    with Vertical(classes="user-controls"):
                        yield Label("Nickname atual:", markup=False)
                        yield Label(self.username, id="current-nickname")
                        yield Input(placeholder="Digite seu nickname", id="username-input", value="")
                        yield Button("Alterar Nick", id="change-nick-btn", variant="primary")
                        yield Label("", id="nick-status")
            
            with Vertical(classes="main-content"):
                yield Log(classes="chat-area", id="chat-log")
                with Horizontal(classes="input-area"):
                    with Horizontal(classes="send-area"):
                        yield Input(placeholder="Digite sua mensagem...", id="message-input", classes="message-input")
                        yield Button("Enviar", id="send-btn", variant="success")
        
        yield Footer()
    
    @on(Select.Changed, "#channel-select")
    async def on_channel_select(self, event: Select.Changed) -> None:
        if event.value != Select.BLANK:
            self.current_channel = str(event.value)
            self.last_message_id = "0"
            
            chat_log = self.query_one("#chat-log", Log)
            chat_log.clear()
            
            chat_log.write_line("=" * 50)
            chat_log.write_line(f"Conectado ao canal #{self.current_channel}")
            chat_log.write_line(f"Logado como {self.username}")
            chat_log.write_line("=" * 50)
            chat_log.write_line("")
            
            await self.load_channel_history()
            self.listen_to_channel()
    
    @on(Button.Pressed, "#change-nick-btn")
    async def on_change_nickname(self) -> None:
        username_input = self.query_one("#username-input", Input)
        new_username = username_input.value.strip()
        
        if new_username:
            if len(new_username) < 2:
                self.update_nick_status("Nickname deve ter pelo menos 2 caracteres", "error")
                return
                
            if len(new_username) > 20:
                self.update_nick_status("Nickname deve ter no máximo 20 caracteres", "error")
                return
                
            old_username = self.username
            self.username = new_username
            username_input.value = ""
            
            current_nick_label = self.query_one("#current-nickname", Label)
            current_nick_label.update(self.username)
            
            self.update_nick_status(f"Nickname alterado para '{self.username}'", "success")
            
            if self.current_channel:
                await self.redis_client.send_message(
                    self.current_channel,
                    "Sistema",
                    f"{old_username} agora é conhecido como {self.username}"
                )
        else:
            self.update_nick_status("Digite um nickname válido", "error")
    
    def update_nick_status(self, message: str, status_type: str) -> None:
        nick_status = self.query_one("#nick-status", Label)
        prefix = "✓" if status_type == "success" else "✗" if status_type == "error" else ""
        nick_status.update(f"{prefix} {message}" if prefix else message)
        self.set_timer(3.0, lambda: nick_status.update(""))
    
    @on(Input.Submitted, "#username-input")
    async def on_username_submit(self) -> None:
        await self.on_change_nickname()

    @on(Button.Pressed, "#create-channel-btn")
    async def on_create_channel(self) -> None:
        new_channel_input = self.query_one("#new-channel-input", Input)
        channel_name = new_channel_input.value.strip()
        
        if channel_name:
            success = await self.redis_client.create_channel(channel_name)
            if success:
                new_channel_input.value = ""
                await self.refresh_channels()
                
                channel_select = self.query_one("#channel-select", Select)
                channel_select.value = channel_name
            else:
                chat_log = self.query_one("#chat-log", Log)
                chat_log.write_line("Erro ao criar canal")
    
    @on(Button.Pressed, "#send-btn")
    async def on_send_message(self) -> None:
        await self.send_message()
    
    @on(Input.Submitted, "#message-input")
    async def on_message_submit(self) -> None:
        await self.send_message()
    
    async def send_message(self) -> None:
        if not self.current_channel:
            return
            
        message_input = self.query_one("#message-input", Input)
        message = message_input.value.strip()
        
        if message:
            success = await self.redis_client.send_message(
                self.current_channel, 
                self.username, 
                message
            )
            if success:
                message_input.value = ""
            else:
                chat_log = self.query_one("#chat-log", Log)
                chat_log.write_line("Erro ao enviar mensagem")
    
    async def load_channel_history(self) -> None:
        if not self.current_channel:
            return
            
        messages = await self.redis_client.get_messages(self.current_channel, "0")
        
        for msg in messages:
            self.display_message(msg)
            self.last_message_id = msg["id"]
    
    @work(exclusive=True)
    async def listen_to_channel(self) -> None:
        if not self.current_channel:
            return
            
        async for message in self.redis_client.listen_for_messages(
            self.current_channel, 
            self.last_message_id
        ):
            self.display_message(message)
            self.last_message_id = message["id"]
    
    def display_message(self, message: Dict) -> None:
        chat_log = self.query_one("#chat-log", Log)
        timestamp = datetime.fromtimestamp(message["timestamp"]).strftime("%H:%M:%S")
        
        if message["type"] == "system":
            chat_log.write_line("-" * 40)
            chat_log.write_line(f"SISTEMA: {message['message']}")
            chat_log.write_line("-" * 40)
        else:
            username = message["username"]
            text = message["message"]
            
            if username == self.username:
                chat_log.write_line(f"[{timestamp}] {username} (você): {text}")
            else:
                chat_log.write_line(f"[{timestamp}] {username}: {text}")
            
            chat_log.write_line("")
    
    async def refresh_channels(self) -> None:
        channels = await self.redis_client.get_channels()
        channel_select = self.query_one("#channel-select", Select)
        options = [(channel, channel) for channel in sorted(channels)]
        channel_select.set_options(options)
    
    def action_refresh_channels(self) -> None:
        self.run_worker(self.refresh_channels())
    
    async def on_unmount(self) -> None:
        await self.redis_client.close()


def main():
    app = ChatApp()
    app.run()

if __name__ == "__main__":
    main()
