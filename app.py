"""
app.py

Streamlit web UI for persona-forge.
Run with: streamlit run app.py

Key design decisions:
- Users bring their own Anthropic API key (entered in sidebar)
- Key lives only in their browser session -- never stored, never logged
- Session-based rate limit: 20 generations per session
- Falls back to ANTHROPIC_API_KEY env var if set (useful for local dev)
- Detects both pre-built personas and custom scraped ones
"""

import os
import anthropic
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from embedder.embed import load_collection, query_similar

load_dotenv()

# Pre-built personas shipped with the repo
PREBUILT = {
    "kunalb11":   "Kunal Shah",
    "naval":      "Naval Ravikant",
    "rajshamani": "Raj Shamani",
}

SESSION_LIMIT = 20

st.set_page_config(
    page_title="Persona Forge",
    page_icon="🎭",
    layout="centered",
)

if "generation_count" not in st.session_state:
    st.session_state.generation_count = 0

# Sidebar
with st.sidebar:
    st.header("Setup")

    env_key = os.getenv("ANTHROPIC_API_KEY")
    if env_key:
        anthropic_key = env_key
        st.success("Using API key from .env")
    else:
        anthropic_key = st.text_input(
            "Your Anthropic API key",
            type="password",
            placeholder="sk-ant-...",
            help="Your key is used only in your browser session and never stored.",
        )
        if anthropic_key:
            st.success("Key set for this session.")
        else:
            st.info(
                "Get a free API key at [console.anthropic.com](https://console.anthropic.com). "
                "Each generation costs ~$0.01."
            )

    st.divider()

    remaining = SESSION_LIMIT - st.session_state.generation_count
    st.metric(
        label="Generations this session",
        value=st.session_state.generation_count,
        delta=f"{remaining} remaining",
        delta_color="normal",
    )
    st.caption(f"Limit resets when you refresh. Each generation ~$0.01.")

    st.divider()
    st.markdown(
        "**persona-forge** is open source.\n\n"
        "[View on GitHub](https://github.com/yourusername/persona-forge)"
    )

# Main
st.title("Persona Forge")
st.caption("Write in the style of any public thinker -- powered by their actual words.")

if not anthropic_key:
    st.warning("Add your Anthropic API key in the sidebar to get started.")
    st.stop()

if st.session_state.generation_count >= SESSION_LIMIT:
    st.error(
        f"You've hit the session limit of {SESSION_LIMIT} generations. "
        "Refresh the page to start a new session."
    )
    st.stop()

# Persona detection -- finds both pre-built and custom personas
data_dir = Path("data")
available_handles = []
if data_dir.exists():
    available_handles = [
        d.name.replace("chroma_", "")
        for d in data_dir.iterdir()
        if d.is_dir() and d.name.startswith("chroma_")
    ]

if not available_handles:
    st.warning(
        "No personas set up yet.\n\n"
        "**Pre-built personas (fastest):**\n"
        "```bash\n"
        "python setup.py --all\n"
        "```\n\n"
        "**Custom persona:**\n"
        "```bash\n"
        "python scraper/twitter.py --handle USERNAME\n"
        "python cleaner/clean.py --handle USERNAME\n"
        "python embedder/embed.py --handle USERNAME\n"
        "```"
    )
    st.stop()

# Sort: pre-built first, custom after
prebuilt_available = [h for h in available_handles if h in PREBUILT]
custom_available   = [h for h in available_handles if h not in PREBUILT]
sorted_handles     = prebuilt_available + custom_available

def persona_label(handle: str) -> str:
    if handle in PREBUILT:
        return f"{PREBUILT[handle]}  (@{handle})"
    return f"@{handle}  (custom)"

selected_label = st.selectbox(
    "Choose a persona",
    options=[persona_label(h) for h in sorted_handles],
)
handle = sorted_handles[[persona_label(h) for h in sorted_handles].index(selected_label)]

# Show context in sidebar
with st.sidebar:
    st.divider()
    if handle in PREBUILT:
        st.caption(f"**{PREBUILT[handle]}** is a pre-built persona shipped with persona-forge.")
    else:
        st.caption(f"**@{handle}** is a custom persona you scraped.")

@st.cache_resource
def get_collection(handle: str):
    return load_collection(handle)

with st.spinner(f"Loading {handle}'s style database..."):
    collection = get_collection(handle)

st.divider()

topic = st.text_area(
    "What do you want to write about?",
    placeholder="e.g. Why most startups die from execution, not competition",
    height=100,
)

output_type = st.selectbox(
    "Output format",
    [
        "Tweet thread (3-5 tweets)",
        "Single tweet",
        "LinkedIn post",
        "Short essay paragraph",
    ],
)

generate = st.button(
    "Generate",
    type="primary",
    disabled=not topic.strip(),
    use_container_width=True,
)

if generate:
    st.session_state.generation_count += 1

    with st.spinner("Finding style examples..."):
        examples = query_similar(collection, topic, n_results=8)

    examples_text = "\n\n---\n\n".join(examples)

    system_prompt = f"""You are a writing style assistant. Your job is to write new content 
in the authentic voice and style of @{handle}, based entirely on real examples of their writing.

Here are real examples of how @{handle} writes:

{examples_text}

Study these examples carefully. Notice:
- Sentence length and rhythm
- How they open a thought (provocation? question? blunt statement?)
- Vocabulary choices -- what words do they favor or avoid?
- How they use examples and analogies
- Emotional register -- direct? provocative? calm? contrarian?
- What they DON'T say -- hedging language, corporate speak, filler phrases they avoid

Your output must sound like it came from @{handle}, not like a generic AI.
Do NOT start with "I" -- it breaks their voice.
Do NOT use corporate jargon or motivational-poster language.
Do NOT explain what you're doing -- just write the content."""

    user_message = f"Write a {output_type} about: {topic}"

    with st.spinner("Writing in their style..."):
        try:
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            output = response.content[0].text

        except anthropic.AuthenticationError:
            st.error("Invalid API key. Check the key you entered in the sidebar.")
            st.session_state.generation_count -= 1
            st.stop()

        except anthropic.RateLimitError:
            st.error("Rate limit hit. Wait a moment and try again.")
            st.session_state.generation_count -= 1
            st.stop()

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.session_state.generation_count -= 1
            st.stop()

    st.divider()
    st.subheader(f"Written as @{handle}")
    st.markdown(output)
    st.code(output, language=None)
    st.caption("Use the copy icon above to grab the text.")

    with st.expander("See style examples used for this generation"):
        st.caption(
            f"These are real excerpts from @{handle}'s writing retrieved as the "
            "closest match to your topic. Injected as style references, not copied into output."
        )
        for i, ex in enumerate(examples, 1):
            st.markdown(f"**Example {i}**")
            st.markdown(ex)
            if i < len(examples):
                st.divider()
