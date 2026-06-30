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
from embedder.embed import load_collection, query_similar, build_vector_store
from scraper.twitter import scrape_tweets, save_tweets
from cleaner.clean import clean_all

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
    anthropic_key = st.text_input(
        "Your Anthropic API key",
        value=env_key or "",
        type="password",
        placeholder="sk-ant-...",
        help="Your key is used only in your browser session and never stored.",
    )
    if anthropic_key:
        st.success("Key set for this session.")
    else:
        st.info(
            "Get an API key at [console.anthropic.com](https://console.anthropic.com). "
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
        "[View on GitHub](https://github.com/shrilathashripathi-ui/Persona-Forge)"
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

# Add a new persona straight from the UI (scrape Twitter -> clean -> embed)
with st.expander("➕ Add a new persona from a Twitter/X handle"):
    st.caption(
        "Enter a public Twitter/X handle. We scrape their recent tweets, "
        "build a style database, and add them to the dropdown above. "
        "Requires an Apify token in your `.env` (used for scraping)."
    )
    new_handle = st.text_input(
        "Twitter/X handle (without @)",
        placeholder="e.g. paulg",
        key="new_persona_handle",
    )
    max_tweets = st.slider(
        "How many recent tweets to pull",
        min_value=10, max_value=200, value=50, step=10,
        help="More tweets = richer style, but slower and slightly higher Apify cost.",
    )
    if st.button("Build persona", disabled=not new_handle.strip()):
        clean_handle = new_handle.strip().lstrip("@")
        if not os.getenv("APIFY_API_TOKEN"):
            st.error("No APIFY_API_TOKEN found in .env — scraping needs one.")
        else:
            try:
                with st.status(f"Building @{clean_handle}...", expanded=True) as status:
                    st.write(f"Scraping last {max_tweets} tweets...")
                    tweets = scrape_tweets(clean_handle, max_tweets)
                    save_tweets(tweets, clean_handle)

                    st.write("Cleaning text...")
                    csv_path = clean_all(clean_handle)
                    if csv_path is None:
                        status.update(label="No usable tweets found.", state="error")
                        st.stop()

                    st.write("Embedding into vector database...")
                    build_vector_store(clean_handle)
                    status.update(label=f"@{clean_handle} is ready!", state="complete")
                st.success(f"Added @{clean_handle}. Select it in the dropdown above.")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't build that persona: {e}")

if not available_handles:
    st.warning(
        "No personas set up yet. Add one above, or run `python setup.py --all` "
        "to embed the pre-built personas (Kunal Shah, Naval Ravikant, Raj Shamani)."
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
