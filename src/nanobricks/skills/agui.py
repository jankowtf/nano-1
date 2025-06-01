"""AGUI (Agent GUI) skill for interactive AI interfaces."""

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nanobricks.agent.ai_protocol import (
    BaseAIProtocolAdapter,
    Message,
    ProtocolConfig,
    ProtocolRegistry,
    ProtocolType,
)
from nanobricks.protocol import NanobrickBase
from nanobricks.skill import NanobrickEnhanced, Skill


class ComponentType(Enum):
    """UI component types."""

    TEXT = "text"
    BUTTON = "button"
    INPUT = "input"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SLIDER = "slider"
    TEXTAREA = "textarea"
    IMAGE = "image"
    CHART = "chart"
    TABLE = "table"
    CONTAINER = "container"
    TABS = "tabs"
    FORM = "form"
    DIALOG = "dialog"


@dataclass
class UIComponent:
    """UI component definition."""

    id: str
    type: ComponentType
    props: dict[str, Any] = field(default_factory=dict)
    children: list["UIComponent"] = field(default_factory=list)
    handlers: dict[str, str] = field(default_factory=dict)  # event -> handler_id

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "props": self.props,
            "children": [child.to_dict() for child in self.children],
            "handlers": self.handlers,
        }


@dataclass
class UIState:
    """UI state management."""

    components: dict[str, UIComponent] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    handlers: dict[str, Callable] = field(default_factory=dict)

    def get_value(self, component_id: str) -> Any:
        """Get component value."""
        return self.values.get(component_id)

    def set_value(self, component_id: str, value: Any) -> None:
        """Set component value."""
        self.values[component_id] = value

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "components": {id: comp.to_dict() for id, comp in self.components.items()},
            "values": self.values,
        }


class AGUIProtocolAdapter(BaseAIProtocolAdapter):
    """AGUI protocol adapter implementation."""

    def __init__(self, config: ProtocolConfig):
        """Initialize AGUI adapter."""
        super().__init__(config)
        self._ui_states: dict[str, UIState] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._update_callbacks: list[Callable[[str, UIState], None]] = []

    async def send(self, message: Message) -> None:
        """Send UI update."""
        if not self._connected:
            raise RuntimeError("Not connected")

        # Handle UI updates
        if message.type == "ui_update":
            session_id = message.metadata.get("session_id", "default")
            if session_id in self._ui_states:
                state = self._ui_states[session_id]
                # Update state from message
                if "components" in message.content:
                    for comp_data in message.content["components"]:
                        comp = self._parse_component(comp_data)
                        state.components[comp.id] = comp

                # Notify callbacks
                for callback in self._update_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(session_id, state)
                        else:
                            callback(session_id, state)
                    except Exception:
                        pass

    async def receive(self) -> Message | None:
        """Receive UI event."""
        if not self._connected:
            return None

        try:
            return await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
        except TimeoutError:
            return None

    async def connect(self) -> None:
        """Start AGUI protocol."""
        self._connected = True

    async def disconnect(self) -> None:
        """Stop AGUI protocol."""
        self._connected = False
        self._ui_states.clear()

    def create_session(self, session_id: str) -> UIState:
        """Create new UI session."""
        state = UIState()
        self._ui_states[session_id] = state
        return state

    def get_session(self, session_id: str) -> UIState | None:
        """Get UI session."""
        return self._ui_states.get(session_id)

    def _parse_component(self, data: dict) -> UIComponent:
        """Parse component from data."""
        comp = UIComponent(
            id=data["id"],
            type=ComponentType(data["type"]),
            props=data.get("props", {}),
            handlers=data.get("handlers", {}),
        )

        # Parse children
        for child_data in data.get("children", []):
            comp.children.append(self._parse_component(child_data))

        return comp

    async def emit_event(self, session_id: str, event: dict) -> None:
        """Emit UI event."""
        message = Message(
            id=str(uuid.uuid4()),
            type="ui_event",
            content=event,
            metadata={"session_id": session_id},
        )
        await self._event_queue.put(message)

    def on_update(self, callback: Callable[[str, UIState], None]) -> None:
        """Register update callback."""
        self._update_callbacks.append(callback)


# Register AGUI adapter
ProtocolRegistry.register(ProtocolType.AGUI, AGUIProtocolAdapter)


class UIBuilder:
    """Fluent UI builder."""

    def __init__(self):
        """Initialize builder."""
        self._components: list[UIComponent] = []

    def text(self, content: str, **props) -> "UIBuilder":
        """Add text component."""
        comp = UIComponent(
            id=f"text_{uuid.uuid4().hex[:8]}",
            type=ComponentType.TEXT,
            props={"content": content, **props},
        )
        self._components.append(comp)
        return self

    def button(self, label: str, on_click: str | None = None, **props) -> "UIBuilder":
        """Add button component."""
        comp = UIComponent(
            id=f"button_{uuid.uuid4().hex[:8]}",
            type=ComponentType.BUTTON,
            props={"label": label, **props},
        )
        if on_click:
            comp.handlers["click"] = on_click
        self._components.append(comp)
        return self

    def input(
        self, placeholder: str = "", default_value: str = "", **props
    ) -> "UIBuilder":
        """Add input component."""
        comp = UIComponent(
            id=f"input_{uuid.uuid4().hex[:8]}",
            type=ComponentType.INPUT,
            props={"placeholder": placeholder, "defaultValue": default_value, **props},
        )
        self._components.append(comp)
        return self

    def select(
        self, options: list[str], default: str | None = None, **props
    ) -> "UIBuilder":
        """Add select component."""
        comp = UIComponent(
            id=f"select_{uuid.uuid4().hex[:8]}",
            type=ComponentType.SELECT,
            props={"options": options, "defaultValue": default, **props},
        )
        self._components.append(comp)
        return self

    def container(self, children: list[UIComponent], **props) -> "UIBuilder":
        """Add container component."""
        comp = UIComponent(
            id=f"container_{uuid.uuid4().hex[:8]}",
            type=ComponentType.CONTAINER,
            props=props,
            children=children,
        )
        self._components.append(comp)
        return self

    def form(
        self, children: list[UIComponent], on_submit: str | None = None, **props
    ) -> "UIBuilder":
        """Add form component."""
        comp = UIComponent(
            id=f"form_{uuid.uuid4().hex[:8]}",
            type=ComponentType.FORM,
            props=props,
            children=children,
        )
        if on_submit:
            comp.handlers["submit"] = on_submit
        self._components.append(comp)
        return self

    def build(self) -> list[UIComponent]:
        """Build components."""
        return self._components


class SkillAGUI(Skill):
    """Agent GUI skill for interactive interfaces."""

    def __init__(
        self,
        adapter: AGUIProtocolAdapter | None = None,
        session_id: str | None = None,
        auto_render: bool = True,
    ):
        """Initialize AGUI skill."""
        super().__init__()
        self._adapter = adapter
        self.session_id = session_id or str(uuid.uuid4())
        self._auto_render = auto_render
        self._ui_state: UIState | None = None
        self._event_handlers: dict[str, Callable] = {}

    def _create_enhanced_brick(self, brick: NanobrickBase) -> NanobrickEnhanced:
        """Create enhanced brick with AGUI capabilities."""

        class AGUINanobrickEnhanced(NanobrickEnhanced):
            """Brick enhanced with AGUI."""

            def __init__(self, wrapped: NanobrickBase, skill: SkillAGUI):
                """Initialize enhanced brick."""
                super().__init__(wrapped, skill)
                self._agui_skill = skill

            async def invoke(self, input: Any, *, deps: dict | None = None) -> Any:
                """Invoke with AGUI capabilities."""
                # Connect if not connected
                if (
                    not self._agui_skill._adapter
                    or not self._agui_skill._adapter.is_connected()
                ):
                    await self._agui_skill.connect()

                # Create UI if auto-render
                if self._agui_skill._auto_render:
                    ui = self._agui_skill.create_ui()
                    await self._agui_skill.render(ui)

                # Process input
                result = await self.wrapped.invoke(input, deps=deps)

                # Update UI with result if configured
                if self._agui_skill._auto_render and result:
                    await self._agui_skill.update_ui({"result": result})

                return result

            def invoke_sync(self, input: Any, *, deps: dict | None = None) -> Any:
                """Sync invoke."""
                return asyncio.run(self.invoke(input, deps=deps))

            def create_ui(self) -> UIBuilder:
                """Create UI builder."""
                return self._agui_skill.create_ui()

            async def render(self, components: list[UIComponent] | UIBuilder) -> None:
                """Render UI components."""
                await self._agui_skill.render(components)

            async def update_ui(self, updates: dict[str, Any]) -> None:
                """Update UI state."""
                await self._agui_skill.update_ui(updates)

            def on_event(self, event_id: str, handler: Callable) -> None:
                """Register event handler."""
                self._agui_skill.on_event(event_id, handler)

            async def show_dialog(
                self,
                title: str,
                content: str | list[UIComponent],
                buttons: list[str] = ["OK"],
            ) -> str:
                """Show dialog and wait for response."""
                return await self._agui_skill.show_dialog(title, content, buttons)

        return AGUINanobrickEnhanced(brick, self)

    async def connect(self, endpoint: str | None = None) -> None:
        """Connect to AGUI system."""
        # Create adapter if not provided
        if not self._adapter:
            config = ProtocolConfig(
                protocol_type=ProtocolType.AGUI,
                endpoint=endpoint,
            )
            self._adapter = ProtocolRegistry.create(config)

        # Connect adapter
        await self._adapter.connect()

        # Create session
        self._ui_state = self._adapter.create_session(self.session_id)

        # Start event handler
        asyncio.create_task(self._handle_events())

    async def disconnect(self) -> None:
        """Disconnect from AGUI system."""
        if self._adapter:
            await self._adapter.disconnect()

    def create_ui(self) -> UIBuilder:
        """Create UI builder."""
        return UIBuilder()

    async def render(self, components: list[UIComponent] | UIBuilder) -> None:
        """Render UI components."""
        if isinstance(components, UIBuilder):
            components = components.build()

        # Update UI state
        for comp in components:
            self._ui_state.components[comp.id] = comp

            # Register handlers
            for event, handler_id in comp.handlers.items():
                if handler_id in self._event_handlers:
                    # Link component to handler
                    comp.handlers[event] = handler_id

        # Send update
        message = Message(
            id=str(uuid.uuid4()),
            type="ui_update",
            content={"components": [comp.to_dict() for comp in components]},
            metadata={"session_id": self.session_id},
        )
        await self._adapter.send(message)

    async def update_ui(self, updates: dict[str, Any]) -> None:
        """Update UI state."""
        # Update values
        for key, value in updates.items():
            self._ui_state.set_value(key, value)

        # Send update
        message = Message(
            id=str(uuid.uuid4()),
            type="ui_update",
            content={"values": updates},
            metadata={"session_id": self.session_id},
        )
        await self._adapter.send(message)

    def on_event(self, event_id: str, handler: Callable) -> None:
        """Register event handler."""
        self._event_handlers[event_id] = handler

    async def show_dialog(
        self, title: str, content: str | list[UIComponent], buttons: list[str] = ["OK"]
    ) -> str:
        """Show dialog and wait for response."""
        dialog_id = f"dialog_{uuid.uuid4().hex[:8]}"
        result_future = asyncio.Future()

        # Build dialog
        dialog_content = []
        if isinstance(content, str):
            dialog_content.append(
                UIComponent(
                    id=f"dialog_text_{uuid.uuid4().hex[:8]}",
                    type=ComponentType.TEXT,
                    props={"content": content},
                )
            )
        else:
            dialog_content = content

        # Add buttons
        button_components = []
        for button_label in buttons:
            button_id = f"dialog_button_{button_label}_{uuid.uuid4().hex[:8]}"
            button_components.append(
                UIComponent(
                    id=button_id,
                    type=ComponentType.BUTTON,
                    props={"label": button_label},
                    handlers={"click": button_id},
                )
            )

            # Register handler
            def make_handler(label):
                async def handler(event):
                    result_future.set_result(label)

                return handler

            self.on_event(button_id, make_handler(button_label))

        # Create dialog component
        dialog = UIComponent(
            id=dialog_id,
            type=ComponentType.DIALOG,
            props={"title": title, "open": True},
            children=dialog_content + button_components,
        )

        # Render dialog
        await self.render([dialog])

        # Wait for result
        return await result_future

    async def _handle_events(self) -> None:
        """Handle UI events."""
        while self._adapter and self._adapter.is_connected():
            try:
                event_msg = await self._adapter.receive()
                if event_msg and event_msg.type == "ui_event":
                    event = event_msg.content
                    handler_id = event.get("handler_id")

                    if handler_id and handler_id in self._event_handlers:
                        handler = self._event_handlers[handler_id]
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
            except Exception:
                # Continue on errors
                await asyncio.sleep(0.1)
