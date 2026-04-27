import logging
from datetime import datetime
from typing import Any, Optional
from .models import InputParams, TextParams, ImageParams, OutputResult

# Logging Setup

LOG_SEPARATOR = "=" * 80

# Create our own logger (not root) with a dedicated file handler
logger = logging.getLogger("GeminiWrapper")
logger.setLevel(logging.INFO)

# IMPORTANT: Only add handler if not already added (prevents duplicate logs on reimport)
if not logger.handlers:
    handler = logging.FileHandler("gemini.log", mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

# Prevent logs from propagating to root
logger.propagate = False

# Silence other libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("google.genai").setLevel(logging.WARNING)

def _safe_str(value: Any) -> str:
    """Safely convert any value to string for logging."""
    if value is None:
        return "None"
    if isinstance(value, type):
        return value.__name__
    if isinstance(value, (list, tuple)):
        return str([_safe_str(v) for v in value])
    if callable(value):
        return f"<function {value.__name__}>"
    return str(value)


def _log_concise(
    timestamp: str,
    operation_type: str,
    input_params: InputParams,
    text_params: Optional[TextParams],
    image_params: Optional[ImageParams],
    output: OutputResult,
):
    """Logs a single-line success message with key parameters."""
    parts = [
        f"[{timestamp}]",
        f"[{operation_type.upper()}]",
        f"[SUCCESS]",
        f"Model: {output.model_used}",
        f"Tokens: {output.token_usage['input']} in - {output.token_usage['output']} out",
    ]
    
    # Add optional params if used
    if input_params.media:
        parts.append(f"Media: {len(input_params.media)} file(s)")
    if text_params and text_params.response_schema:
        parts.append(f"Schema: {_safe_str(text_params.response_schema)}")
    if text_params and text_params.tools:
        tool_names = [_safe_str(t) for t in text_params.tools]
        parts.append(f"Tools: {tool_names}")
    if image_params and image_params.output_image_aspect_ratio:
        parts.append(f"Aspect: {image_params.output_image_aspect_ratio}")
    
    # Prompt preview (truncated)
    prompt_preview = input_params.prompt.replace("\n", " ").strip()[:80]
    if len(input_params.prompt) > 80:
        prompt_preview += "..."
    parts.append(f'Prompt: "{prompt_preview}"')
    
    logger.info(" | ".join(parts))


def _format_header_section(timestamp: str, operation_type: str, status: str, input_params: InputParams, output: OutputResult) -> list[str]:
    """Formats the header section of the log."""
    return [
        f"\n{LOG_SEPARATOR}",
        f"[{timestamp}] [{operation_type.upper()}] [{status}]",
        f"Model Used: {output.model_used}",
        f"Requested Model: {input_params.model}",
        f"Tokens: Input={output.token_usage['input']}, Output={output.token_usage['output']}",
        f"Retries: {output.retry_attempts}",
    ]

def _format_config_section(input_params: InputParams, text_params: Optional[TextParams], image_params: Optional[ImageParams]) -> list[str]:
    """Formats the configuration section of the log."""
    lines = []
    # Prompt
    lines.append(f"\n--- PROMPT ---\n{input_params.prompt}")
    
    # Media
    if input_params.media:
        lines.append(f"\n--- MEDIA ({len(input_params.media)} files) ---")
        for i, m in enumerate(input_params.media, 1):
            lines.append(f"  {i}. {_safe_str(m)[:200]}")
            
    # Text config
    if text_params:
        if text_params.response_schema:
            lines.append(f"\n--- SCHEMA ---\n{_safe_str(text_params.response_schema)}")
        if text_params.response_mime_type:
            lines.append(f"\n--- RESPONSE MIME TYPE ---\n{text_params.response_mime_type}")
        if text_params.tools:
            lines.append(f"\n--- TOOLS ---")
            for t in text_params.tools:
                lines.append(f"  - {_safe_str(t)}")
    
    # Image config
    has_image_config = (
        (image_params and (image_params.output_image_aspect_ratio or image_params.output_image_size))
        or input_params.processed_image_size
    )
    if has_image_config:
        lines.append(f"\n--- IMAGE CONFIG ---")
        if image_params and image_params.output_image_aspect_ratio:
            lines.append(f"  Aspect Ratio: {image_params.output_image_aspect_ratio}")
    
    return lines

def _log_detailed(
    timestamp: str,
    operation_type: str,
    input_params: InputParams,
    text_params: Optional[TextParams],
    image_params: Optional[ImageParams],
    output: OutputResult,
):
    """Logs detailed multi-line message for failures or retries."""
    status = "SUCCESS_WITH_RETRIES" if output.success else "FAILED"
    
    lines = _format_header_section(timestamp, operation_type, status, input_params, output)
    lines.extend(_format_config_section(input_params, text_params, image_params))
    
    # Error section
    if output.error:
        lines.append(f"\n--- FINAL ERROR ---\n{output.error}")
    if output.error_log:
        lines.append(f"\n--- ERROR HISTORY ({len(output.error_log)} entries) ---")
        for i, e in enumerate(output.error_log, 1):
            lines.append(f"  {i}. {e}")
    
    # Footer
    lines.append(f"{LOG_SEPARATOR}\n")
    
    logger.info("\n".join(lines))


def log_operation(
    operation_type: str,
    input_params: InputParams,
    output: OutputResult,
    text_params: Optional[TextParams] = None,
    image_params: Optional[ImageParams] = None,
):
    """
    Main entry point for logging operations.
    Delegates to _log_concise or _log_detailed based on result.
    """
    timestamp = datetime.now().strftime("%d-%m-%Y, %H:%M:%S")
    
    if output.success and output.retry_attempts == 0:
        # Clean success - use concise format
        _log_concise(
            timestamp=timestamp,
            operation_type=operation_type,
            input_params=input_params,
            text_params=text_params,
            image_params=image_params,
            output=output,
        )
    else:
        # Failure or retries - use detailed format
        _log_detailed(
            timestamp=timestamp,
            operation_type=operation_type,
            input_params=input_params,
            text_params=text_params,
            image_params=image_params,
            output=output,
        )
