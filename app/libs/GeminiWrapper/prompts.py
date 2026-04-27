
def get_media_process_error_prompt(media_type: str, url: str, error: str) -> str:
    """Generate the system note when media processing fails."""
    prompt = [
        f"\n[System Note: The user tried to attach a {media_type} from '{url}' but it failed to load. Error: {error}]"
    ]
    return "\n".join(prompt)
