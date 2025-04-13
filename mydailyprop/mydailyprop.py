"""My Daily Propaganda App."""

from enum import Enum
from operator import add
import os
from typing import Annotated, Any, AsyncGenerator, Dict, List
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain_community.document_loaders import FireCrawlLoader
import reflex as rx  # type: ignore
# Reflex does not provide type hints at the moment

model_name = "gpt-4o-mini"
model = ChatOpenAI(model=model_name, temperature=0.7, streaming=True)


class NewsOutlet(str, Enum):
    LEMONDE = (
        "Le Monde",
        """Le Monde is a French daily newspaper.
It publishes a daily editorial that is signed 'Le Monde'.
Not signed because it represents the views of the entire newspaper, the \
editorial is typically written by one of the four editorial writers of the \
editorial team after a collective process of selecting and taking a stance on \
a current issue."""
    )
    THEGUARDIAN = (
        "The Guardian",
        """The Guardian is a British daily newspaper.
It publishes two daily editorial pieces titled 'The Guardian view on...', \
which are both unsigned.
Though the piece is written mainly by a single author, it is produced through \
a collaborative process involving other journalists, subject specialists, and \
the editor, ensuring that the final unsigned piece reflects a collective \
viewpoint rather than individual opinions."""
    )
    LIBERATION = (
        "Libération",
        """Libération is a French daily newspaper.
It publishes a daily editorial that is signed by a member of the editorial \
board (may be the director)."""
    )

    def __new__(cls, value, editorial_context):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._editorial_context = editorial_context
        return obj

    @property
    def contextualize(self):
        return self._editorial_context


class Editorial(BaseModel):
    title: str = Field(
        ...,
        title="Editorial title")
    outlet: NewsOutlet = Field(
        ...,
        title="Outlet the editorial was published in")
    date: str = Field(
        ...,
        title="Editorial publication date in the format: DD/MM-YYYY")
    language: str = Field(
        ...,
        title="Editorial language (i.e., 'English', 'French', ...)")
    lede: str = Field(
        ...,
        title="Editorial lede")
    body: str = Field(
        ...,
        title="Editorial body")

    def markdown(self) -> str:
        return f"# {self.title} ({self.outlet.value}, {self.date} - \
        {self.language})\n\n**{self.lede}**\n\n{self.body}"


class GraphState(TypedDict):

    url:                    str
    editorial:              Editorial
    news_critique:          str
    psychological_analysis: str
    propaganda_synthesis:   Annotated[str, add]
    # having multiple edges requires at least one Annotated type hint (at
    # least one reducer must be defined - though none will be used here as each
    # node has its own state variable in news_critique and
    # psychological_analysis)


# 'get_contents' Node
_get_contents_prompt = hub.pull("btm-guirriecp/mydailyprop-get_contents:86a0ee93")
_get_contents_chain = _get_contents_prompt | model


def _get_contents(state: GraphState) -> dict[str, Any]:
    loader = FireCrawlLoader(
        api_key=os.getenv('FIRECRAWL_API_KEY'),
        url=state["url"],
        mode="scrape"
    )
    docs = loader.load()
    extracted_json_data = docs[0].page_content

    editorial_dict = _get_contents_chain.invoke({
        "json_data": extracted_json_data, }
    )
    editorial = Editorial.model_validate(editorial_dict)

    return {
        "editorial": editorial,
    }


# 'critique' Node
_critique_prompt = hub.pull("btm-guirriecp/mydailyprop-critique:e72b47f6")
_critique_chain = _critique_prompt | model


def _critique(state: GraphState) -> dict[str, Any]:
    edito = state["editorial"]
    critique = _critique_chain.invoke({
        "news_outlet":          edito.outlet.value,
        "editorial_date":       edito.date,
        "editorial_context":    edito.outlet.contextualize,
        "editorial_content":    edito.markdown(),
    })
    return {
        "news_critique": critique.content
    }


# 'psychological' Node
_psychological_prompt = hub.pull("btm-guirriecp/mydailyprop-psychological:5ac731bc")
_psychological_chain = _psychological_prompt | model


def _psychological(state: GraphState) -> dict[str, Any]:
    edito = state["editorial"]
    psychological = _psychological_chain.invoke({
        "news_outlet":  edito.outlet.value,
        "editorial":    edito.markdown(),
        "date":         edito.date, }
    )
    return {
        "psychological_analysis": psychological.content
    }


# 'synthesis' Node
_synthesis_prompt = hub.pull("btm-guirriecp/mydailyprop-synthesis:a29b8991")
_synthesis_chain = _synthesis_prompt | model


def _synthesis(state: GraphState) -> dict[str, Any]:
    edito = state["editorial"]
    synthesis = _synthesis_chain.invoke({
        "news_outlet":      edito.outlet.value,
        "editorial":        edito.markdown(),
        "date":             edito.date,
        "critique":         state["news_critique"],
        "psychological":    state["psychological_analysis"]}
    )
    return {
        "propaganda_synthesis": synthesis.content
    }


graph_builder = StateGraph(GraphState)

graph_builder.add_node("get_contents", _get_contents)
graph_builder.set_entry_point("get_contents")

graph_builder.add_node("critique", _critique)
graph_builder.add_edge("get_contents", "critique")

graph_builder.add_node("psychological", _psychological)
graph_builder.add_edge("get_contents", "psychological")

graph_builder.add_node("synthesis", _synthesis)
graph_builder.add_edge(["critique", "psychological"], "synthesis")

graph_builder.set_finish_point("synthesis")

graph = graph_builder.compile()

# Displays the graph LangGraph if 'SHOW_GRAPH' is true
# in the environment variable
if os.getenv("SHOW_GRAPH") == "true":
    try:
        from PIL import Image  # type: ignore
        from io import BytesIO
    except ImportError:
        raise ImportError(
            "Could not import PIL python package. "
            "Please install it with `poetry install --with dev`."
        )
    img_data = graph.get_graph().draw_mermaid_png()
    img = Image.open(BytesIO(img_data))
    img.show()


class AppState(rx.State):  # type: ignore
    """The Reflex app state."""

    url: str = ""
    is_running: bool = False
    cards: Dict[str, Dict[str, str]] = {}

    def upsert_card(
        self,
        card_name: str,
        card_desc: str,
        card_content: str,
        color_scheme: str
    ) -> None:
        """Insert or update a card at the beginning of the cards dictionary."""
        if card_name in self.cards:
            self.cards[card_name]["content"] += card_content
        else:
            new_dict_entry = {card_name: {
                "desc": card_desc,
                "content": card_content,
                "color_scheme": color_scheme}}
            self.cards = {**new_dict_entry, **self.cards}

    async def decrypt(self) -> AsyncGenerator[None, None]:
        """Decrypt the URL contents."""

        self.is_running = True
        # reset the cards
        self.cards = {}
        yield

        # return if url is empty
        if not self.url:
            self.is_running = False
            return

        # invoke graph with the URL
        async for event in graph.astream_events(
            {"url":  self.url},
            version="v2"
        ):
            kind = event["event"]
            # emitted for each streamed token
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                # only print non-empty content (not tool calls)
                if content:
                    origin_node = event["metadata"]["langgraph_node"]
                    if origin_node == "critique":
                        self.upsert_card(
                            card_name="critique",
                            card_desc="Journalistic evaluation (generated)",
                            card_content=content,
                            color_scheme="indigo")
                    elif origin_node == "psychological":
                        self.upsert_card(
                            card_name="psychological",
                            card_desc="Psychological analysis (generated)",
                            card_content=content,
                            color_scheme="mint")
                    elif origin_node == "synthesis":
                        self.upsert_card(
                            card_name="synthesis",
                            card_desc="Propaganda synthesis (generated)",
                            card_content=content,
                            color_scheme="crimson")
                    yield
            # emitted when a model call finishes (we want to catch the
            # Editorial's contents extraction as JSON using
            # with_structured_output (using 'functions' / 'tools')
            if kind == "on_chat_model_end":
                # using 'functions' / 'tools' creates an event with tool_calls
                if event["data"]["output"].tool_calls:
                    edito_dict = event["data"]['output'].tool_calls[0]['args']
                    self.upsert_card(
                        card_name="editorial",
                        card_desc="Editorial contents (extracted)",
                        card_content=Editorial(**edito_dict).markdown(),
                        color_scheme="blue")
            yield

        self.is_running = False


def action_bar() -> rx.Component:
    return rx.hstack(
        rx.input(
            placeholder="Enter URL here...",
            on_change=AppState.set_url,
            flex_grow="1",
        ),
        rx.button(
            "decrypt",
            on_click=AppState.decrypt,
            loading=AppState.is_running,
        ),
        width="80%",
    )


def content_card(card_contents: List[Any]) -> rx.Component:
    return rx.card(
        rx.scroll_area(
            rx.heading(
                card_contents[1]["desc"],
                color_scheme=card_contents[1]["color_scheme"],
                size="3"
            ),
            rx.markdown(
                card_contents[1]["content"],
                width="98%",
            ),
            type="always",
            scrollbars="vertical",
            style={"height": 250},
        ),
    )


def index() -> rx.Component:
    return rx.container(
        rx.color_mode.button(position="top-right"),
        rx.vstack(
            rx.heading("My Daily Propaganda", size="9"),
            rx.text(
                "decrypted ",
                rx.code("@ Brest Thinking Machines"),
                size="5",
            ),
            action_bar(),
            rx.text(
                f"All contents generated using {model_name!r}, \
                and may be human-level BS.",
                align="center",
                color_scheme="gray",
                size="1",
            ),
            rx.foreach(
                AppState.cards,
                content_card,
            ),
            spacing="5",
            justify="center",
            align="center",
            min_height="85vh",
        ),
        rx.logo(),
    )


app = rx.App()
app.add_page(index, title="My Daily Propaganda")
