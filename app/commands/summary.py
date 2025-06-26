import os
import click
from ..services.summary import correct_transcript, summarize_transcript, configure_api
from ..config import settings

def do_correct(input, output, provider, model, api_key):
    """Implementation logic for transcript correction"""
    if not api_key:
        api_key = settings.config.get(f"{provider}_api_key", None)
    
    configure_api(provider=provider, api_key=api_key)
    
    with open(input, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    corrected_text = correct_transcript(original_text, provider=provider, model_name=model)
    
    if corrected_text:
        if not output:
            base_name = os.path.splitext(os.path.basename(input))[0]
            input_dir = os.path.dirname(input) or "."
            output = os.path.join(input_dir, f"{base_name}_corrected.txt")
            
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            f.write(corrected_text)
        click.echo(f"Corrected transcript saved to: {output}")

def do_summarize(input, output, provider, model, api_key, correct_first):
    """Implementation logic for transcript summarization"""
    if not api_key:
        api_key = settings.config.get(f"{provider}_api_key", None)
    
    configure_api(provider=provider, api_key=api_key)
    
    with open(input, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    text_to_summarize = original_text
    
    if correct_first:
        click.echo("Correcting transcript before summarization...")
        text_to_summarize = correct_transcript(original_text, provider=provider, model_name=model)
    
    summary_text = summarize_transcript(text_to_summarize, provider=provider, model_name=model)
    
    if summary_text:
        if not output:
            base_name = os.path.splitext(os.path.basename(input))[0]
            input_dir = os.path.dirname(input) or "."
            output = os.path.join(input_dir, f"{base_name}_summary.txt")
            
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        click.echo(f"Summary saved to: {output}")

@click.group()
def summary():
    """Transcript correction and summarization commands."""
    pass

@summary.command()
@click.option("--input", "-i", required=True, help="Path to input transcript file.")
@click.option("--output", "-o", help="Path to save corrected transcript.")
@click.option("--provider", default="gemini", type=click.Choice(["gemini", "openai", "claude"]), help="AI provider to use.")
@click.option("--model", help="Model name to use with the selected provider.")
@click.option("--api-key", help="Custom API key for the selected provider.")
def correct(input, output, provider, model, api_key):
    """Correct transcription errors in the transcript."""
    do_correct(input, output, provider, model, api_key)

@summary.command()
@click.option("--input", "-i", required=True, help="Path to input transcript file.")
@click.option("--output", "-o", help="Path to save summary.")
@click.option("--provider", default="gemini", type=click.Choice(["gemini", "openai", "claude"]), help="AI provider to use.")
@click.option("--model", help="Model name to use with the selected provider.")
@click.option("--api-key", help="Custom API key for the selected provider.")
@click.option("--correct-first/--no-correct", default=False, help="Correct transcript before summarizing.")
def summarize(input, output, provider, model, api_key, correct_first):
    """Generate a summary of the transcript."""
    do_summarize(input, output, provider, model, api_key, correct_first)

@click.command(name="correct")
@click.option("--input", "-i", required=True, help="Path to input transcript file.")
@click.option("--output", "-o", help="Path to save corrected transcript.")
@click.option("--provider", default="gemini", type=click.Choice(["gemini", "openai", "claude"]), help="AI provider to use.")
@click.option("--model", help="Model name to use with the selected provider.")
@click.option("--api-key", help="Custom API key for the selected provider.")
def correct_command(input, output, provider, model, api_key):
    """Correct transcription errors in the transcript."""
    do_correct(input, output, provider, model, api_key)

@click.command(name="summarize")
@click.option("--input", "-i", required=True, help="Path to input transcript file.")
@click.option("--output", "-o", help="Path to save summary.")
@click.option("--provider", default="gemini", type=click.Choice(["gemini", "openai", "claude"]), help="AI provider to use.")
@click.option("--model", help="Model name to use with the selected provider.")
@click.option("--api-key", help="Custom API key for the selected provider.")
@click.option("--correct-first/--no-correct", default=False, help="Correct transcript before summarizing.")
def summarize_command(input, output, provider, model, api_key, correct_first):
    """Generate a summary of the transcript."""
    do_summarize(input, output, provider, model, api_key, correct_first)