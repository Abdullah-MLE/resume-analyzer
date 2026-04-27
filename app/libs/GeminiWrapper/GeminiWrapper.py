"""
Gemini Wrapper Class

A production-ready OOP wrapper for the Google GenAI SDK (google-genai).
Provides simplified interfaces for text, image, audio, video, and tool calling.
"""

import time
import requests
import io
import logging
from PIL import Image
from typing import Any, Callable, Dict, List, Optional
from google import genai
from google.genai import types

from dotenv import load_dotenv
from .prompts import get_media_process_error_prompt
from .config import config
from .models import InputParams, TextParams, ImageParams, OutputResult
from .logger_config import log_operation

load_dotenv()


# Gemini Wrapper Class

class GeminiWrapper:
    """
    Main wrapper class for Gemini API operations.
    Handles text generation, image generation, and media processing.
    """
    
    def __init__(self, client: Optional[genai.Client] = None):
        """
        Initialize the Gemini wrapper.
        
        Args:
            client: Optional Gemini client. If None, creates a new one.
        """
        self.client = client or genai.Client()
        self.logger = logging.getLogger("GeminiWrapper")
    
    # Public Methods
    
    def generate_text(
        self,
        input_params: InputParams,
        text_params: Optional[TextParams] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate text using Gemini's text generation capabilities.
        
        Args:
            input_params: Input parameters (prompt, media, etc.)
            text_params: Text generation parameters (schema, tools, etc.)
            **kwargs: Additional config parameters
            
        Returns:
            Dict with content, model_used, token_usage, success, error, etc.
        """
        # Initialize params
        if text_params is None:
            text_params = TextParams()
        
        # Get models to try
        model = input_params.model or config.default_text_model
        models_to_try = self._prioritize_models(model, config.text_fallback_models)
        
        # Prepare inputs
        gen_config, contents = self._prepare_model_inputs(
            input_params=input_params,
            text_params=text_params,
            **kwargs
        )
        
        # Define text extractor
        def extract_text(response):
            """Extracts text from the response."""
            result = response.parsed if text_params.response_schema else response.text
            
            # Re-instantiate Pydantic model if we got a dict but expected a model class
            if text_params.response_schema and isinstance(result, dict):
                try:
                    # Check if response_schema is a Pydantic model class
                    if hasattr(text_params.response_schema, "model_validate"):
                        return text_params.response_schema.model_validate(result)
                    elif isinstance(text_params.response_schema, type):
                        return text_params.response_schema(**result)
                except Exception as e:
                    # If conversion fails, fallback to dict but log it
                    self.logger.warning(f"Failed to convert dict to Pydantic model: {e}")
            
            return result
        
        # Execute with retry
        output = self._execute_with_retry(
            models_to_try=models_to_try,
            contents=contents,
            gen_config=gen_config,
            result_extractor=extract_text,
            max_retries_per_model=config.text_max_retries_per_model,
            overall_max_retries=config.text_overall_max_retries,
            operation_name="Text generation",
        )
        
        return self._finalize_and_log(
            operation_type="TEXT",
            input_params=input_params,
            output=output,
            text_params=text_params,
        )
    
    def generate_image(
        self,
        input_params: InputParams,
        image_params: Optional[ImageParams] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate an image using Gemini's image generation capabilities.
        
        Args:
            input_params: Input parameters (prompt, media, etc.)
            image_params: Image generation parameters (aspect ratio, etc.)
            **kwargs: Additional config parameters
            
        Returns:
            Dict with content (image bytes), model_used, token_usage, etc.
        """
        # Initialize params
        if image_params is None:
            image_params = ImageParams()
        
        # Get models to try
        model = input_params.model or config.default_image_model
        models_to_try = self._prioritize_models(model, config.image_models)
        
        # Prepare inputs
        gen_config, contents = self._prepare_model_inputs(
            input_params=input_params,
            image_params=image_params,
            **kwargs
        )
        
        # Define image extractor
        def extract_image(response):
            """Extracts image bytes from the response."""
            image_bytes = self._extract_image_from_response(response)
            if not image_bytes:
                raise ValueError("No image data found in response parts.")
            return image_bytes
        
        # Execute with retry
        output = self._execute_with_retry(
            models_to_try=models_to_try,
            contents=contents,
            gen_config=gen_config,
            result_extractor=extract_image,
            max_retries_per_model=config.image_max_retries_per_model,
            overall_max_retries=config.image_overall_max_retries,
            operation_name="Image generation",
        )
        
        return self._finalize_and_log(
            operation_type="IMAGE",
            input_params=input_params,
            output=output,
            image_params=image_params,
        )
    
    # Private Helper Methods - Execution & Retry Logic
    
    def _execute_with_retry(
        self,
        models_to_try: List[str],
        contents: List[types.Content],
        gen_config: types.GenerateContentConfig,
        result_extractor: Callable,
        max_retries_per_model: int,
        overall_max_retries: int,
        operation_name: str = "Operation",
    ) -> OutputResult:
        """
        Execute Gemini API call with retry logic across multiple models.
        
        Returns:
            OutputResult model with content, success status, errors, etc.
        """
        error_log = []
        retry_attempts = 0
        model_used = models_to_try[0] if models_to_try else "unknown"
        
        for current_model in models_to_try:
            for attempt in range(max_retries_per_model):
                # Check global retry limit
                if retry_attempts >= overall_max_retries:
                    return OutputResult(
                        content=None,
                        model_used=model_used,
                        success=False,
                        error=f"Max overall retries ({overall_max_retries}) reached",
                        retry_attempts=retry_attempts,
                        error_log=error_log,
                    )
                
                try:
                    # Make API call
                    response = self.client.models.generate_content(
                        model=current_model,
                        contents=contents,
                        config=gen_config,
                    )
                    
                    # Extract result
                    content = result_extractor(response)
                    
                    # Success!
                    return OutputResult(
                        content=content,
                        model_used=current_model,
                        token_usage=self._extract_token_usage(response),
                        success=True,
                        error=None,
                        retry_attempts=retry_attempts,
                        error_log=error_log,
                        raw_response=response,
                    )
                    
                except Exception as e:
                    retry_attempts += 1
                    error_log.append(f"{operation_name} failed ({current_model}): {str(e)}")
                    
                    if attempt < max_retries_per_model - 1:
                        time.sleep(config.retry_delay_seconds)
            
            # Check if max retries reached
            if retry_attempts >= overall_max_retries:
                break
        
        # All retries exhausted
        return OutputResult(
            content=None,
            model_used=model_used,
            success=False,
            error=f"{operation_name} failed after all retries.",
            retry_attempts=retry_attempts,
            error_log=error_log,
        )
    
    # Private Helper Methods - Input Preparation
    
    def _prepare_model_inputs(
        self,
        input_params: InputParams,
        text_params: Optional[TextParams] = None,
        image_params: Optional[ImageParams] = None,
        **kwargs
    ) -> tuple[Any, List[types.Content]]:
        """
        Prepare config and contents for Gemini API call.
        
        Returns:
            Tuple of (config, contents)
        """
        # Process media and build parts
        parts, final_prompt = self._process_media_to_parts(
            prompt=input_params.prompt,
            media=input_params.media,
            processed_image_size=input_params.processed_image_size,
        )
        
        # Build contents
        contents = self._build_contents(parts)
        
        # Build config
        gen_config = self._build_config(
            system_instruction=input_params.system_instruction,
            text_params=text_params,
            image_params=image_params,
            media_resolution=input_params.media_resolution,
            **kwargs
        )
        
        return gen_config, contents
    
    def _process_media_to_parts(
        self,
        prompt: str,
        media: Optional[List[str]] = None,
        processed_image_size: Optional[int] = config.default_image_max_dimension,
    ) -> tuple[List[types.Part], str]:
        """
        Download and process media files into Gemini Parts.
        Supports images, audio, video, and YouTube URLs.
        
        Returns:
            Tuple of (parts_list, final_prompt)
        """
        parts = []
        final_prompt = prompt
        
        if media:
            for url in media:
                try:
                    # Check if YouTube URL
                    if "youtube.com" in url.lower() or "youtu.be" in url.lower():
                        # YouTube - use FileData
                        parts.append(types.Part(
                            file_data=types.FileData(file_uri=url)
                        ))
                    else:
                        # Regular media - download
                        media_bytes, mime_type = self._download_media(url)
                        
                        # Resize if image
                        if mime_type.startswith("image/"):
                            media_bytes = self._resize_image(media_bytes, processed_image_size)
                        
                        # Add as bytes
                        parts.append(types.Part.from_bytes(data=media_bytes, mime_type=mime_type))
                
                except Exception as e:
                    # Add error to prompt
                    err_msg = str(e)
                    final_prompt += get_media_process_error_prompt("media", url, err_msg)
        
        # Add text prompt as last part
        parts.append(types.Part(text=final_prompt))
        
        return parts, final_prompt
    
    def _build_contents(self, parts: List[types.Part]) -> List[types.Content]:
        """Wrap parts in a user Content object."""
        return [
            types.Content(
                role="user",
                parts=parts
            )
        ]
    
    def _build_config(
        self,
        system_instruction: Optional[str] = None,
        text_params: Optional[TextParams] = None,
        image_params: Optional[ImageParams] = None,
        media_resolution: Optional[str] = None,
        **kwargs
    ) -> types.GenerateContentConfig:
        """Build the GenerateContentConfig with all parameters."""
        config_params = {}
        
        # System instruction
        config_params["system_instruction"] = system_instruction
        
        # Media resolution
        if media_resolution:
            config_params["media_resolution"] = media_resolution
        
        # Text generation config
        if text_params:
            if text_params.response_schema:
                # Use response_json_schema to bypass SDK additionalProperties validation
                schema = text_params.response_schema
                if hasattr(schema, "model_json_schema"):
                    config_params["response_json_schema"] = schema.model_json_schema()
                else:
                    config_params["response_json_schema"] = schema
                
                config_params["response_mime_type"] = text_params.response_mime_type
            if text_params.tools:
                config_params["tools"] = text_params.tools
                if text_params.tool_config:
                    config_params["tool_config"] = text_params.tool_config
        
        # Image generation config
        if image_params and image_params.output_image_aspect_ratio:
            config_params["response_modalities"] = ["TEXT", "IMAGE"]
            config_params["image_config"] = types.ImageConfig(
                aspect_ratio=image_params.output_image_aspect_ratio,
            )
        
        # Extra kwargs
        config_params.update(kwargs)
        
        return types.GenerateContentConfig(**config_params)
    
    # Private Helper Methods - Media Processing
    
    def _download_media(self, url: str) -> tuple[bytes, str]:
        """Download media from URL and return (bytes, mime_type)."""
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "application/octet-stream")
            return response.content, mime_type
        except Exception as e:
            raise e
    
    def _resize_image(
        self,
        image_bytes: bytes,
        max_dimension: Optional[int] = config.default_image_max_dimension
    ) -> bytes:
        """
        Resize image if dimensions exceed max_dimension.
        Maintains aspect ratio. Does NOT upscale.
        """
        if not max_dimension:
            return image_bytes
        
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                
                # Check if resizing needed
                if width <= max_dimension and height <= max_dimension:
                    return image_bytes
                
                # Calculate new dimensions
                scale_factor = min(max_dimension / width, max_dimension / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                
                # Resize
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = io.BytesIO()
                fmt = img.format if img.format else 'JPEG'
                resized_img.save(output, format=fmt)
                return output.getvalue()
                
        except Exception as e:
            self.logger.warning(f"Image resizing failed: {e}")
            return image_bytes
    
    # Private Helper Methods - Response Extraction
    
    def _extract_image_from_response(self, response: Any) -> Optional[bytes]:
        """Extract binary image data from Gemini response."""
        # Check candidates first
        if hasattr(response, 'candidates') and response.candidates:
            if response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        return part.inline_data.data
        
        # Fallback to direct parts
        if hasattr(response, 'parts') and response.parts:
            for part in response.parts:
                if part.inline_data:
                    return part.inline_data.data
        
        return None
    
    def _extract_token_usage(self, response: Any) -> Dict[str, int]:
        """Extract token usage from Gemini response."""
        try:
            usage = response.usage_metadata
            return {
                "input": usage.prompt_token_count or 0,
                "output": usage.candidates_token_count or 0,
            }
        except (AttributeError, TypeError):
            return {"input": 0, "output": 0}
    
    # Private Helper Methods - Utilities
    
    def _prioritize_models(
        self,
        requested_model: Optional[str],
        default_models: List[str]
    ) -> List[str]:
        """Reorder model list to prioritize requested model."""
        models_to_try = default_models.copy()
        if requested_model:
            if requested_model in models_to_try:
                models_to_try.remove(requested_model)
                models_to_try.insert(0, requested_model)
            else:
                models_to_try.insert(0, requested_model)
        return models_to_try
    
    def _finalize_and_log(
        self,
        operation_type: str,
        input_params: InputParams,
        output: OutputResult,
        text_params: Optional[TextParams] = None,
        image_params: Optional[ImageParams] = None,
    ) -> Dict[str, Any]:
        """
        Create standardized response dictionary and log the operation.
        """
        # Log operation
        log_operation(
            operation_type=operation_type,
            input_params=input_params,
            output=output,
            text_params=text_params,
            image_params=image_params,
        )
        
        # Return standardized response
        return {
            "content": output.content,
            "model_used": output.model_used,
            "token_usage": output.token_usage,
            "success": output.success,
            "error": output.error,
            "retry_attempts": output.retry_attempts,
            "error_log": output.error_log,
            "raw_response": output.raw_response,
        }


# Convenience Function

def init_gemini_client():
    """Initialize and return a Gemini client."""
    return genai.Client()


# Usage Example

if __name__ == "__main__":
    # Example usage
    wrapper = GeminiWrapper()
    
    # Text generation
    # text_result = wrapper.generate_text(
    #     input_params=InputParams(
    #         prompt="Tell me a joke about programming",
    #     )
    # )
    # print("Text:", text_result["content"])
    
    # Image generation
    image_result = wrapper.generate_image(
        input_params=InputParams(
            prompt="A cute robot coding on a laptop",
        ),
        image_params = ImageParams(
            output_image_aspect_ratio="1:1"
        )
    )
    print("Image generated:", image_result["success"])
