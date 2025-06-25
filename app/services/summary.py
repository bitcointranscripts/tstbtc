import os
import google.generativeai as genai
import argparse
import getpass
from dotenv import load_dotenv
import openai
import anthropic
load_dotenv() 


def configure_api(provider="gemini", api_key=None):
    if provider == "gemini":
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not provided and not found in environment.")
        genai.configure(api_key=api_key)
        print("Gemini API configured successfully.")
    elif provider == "openai":
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not provided and not found in environment.")
        openai.api_key = api_key
        print("OpenAI API configured successfully.")
    elif provider == "claude":
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Claude API key not provided and not found in environment.")
        print("Claude API configured successfully.")
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    return api_key


def create_correction_prompt(transcript_text):
    return f"""
You are an expert in Bitcoin, Monero, and blockchain technologies.
The transcript below was generated from a conference audio recording using automatic speech recognition (ASR) and may contain misrecognized or misspelled technical terms.

Your task is to correct all errors in the transcript while strictly following these rules:
1.  Correct all misspelled or misrecognized Bitcoin and Monero-specific terms.
2.  Capitalize technical terms and proper nouns correctly.
3.  Remove ASR artifacts like stutters and false starts.
4.  Remove nonsensical or duplicated lines.
5.  Preserve the original sentence structure and meaning.
6.  Only output the corrected transcript text.

--- START OF TRANSCRIPT TO CORRECT ---

{transcript_text}

--- END OF TRANSCRIPT TO CORRECT ---
"""


def create_summary_prompt(text):
    return f"""
You are an expert technical summarizer.

Summarize the following transcript of a conference talk about Bitcoin and Monero. Your summary should be concise and cover all the key points mentioned by the speaker. Avoid repeating unnecessary phrases or filler words. Output only the summary, without introduction or conclusion lines.

--- START OF TRANSCRIPT ---

{text}

--- END OF TRANSCRIPT ---
"""


def correct_transcript(text_to_correct, provider="gemini", model_name=None):
    prompt = create_correction_prompt(text_to_correct)
    
    if provider == "gemini":
        return correct_transcript_with_gemini(text_to_correct, model_name)
    elif provider == "openai":
        return correct_transcript_with_openai(text_to_correct, model_name)
    elif provider == "claude":
        return correct_transcript_with_claude(text_to_correct, model_name)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def correct_transcript_with_gemini(text_to_correct, model_name=None):
    model = genai.GenerativeModel(model_name or 'gemma-3-27b-it')
    prompt = create_correction_prompt(text_to_correct)
    try:
        print("Sending correction request to Gemini API...")
        response = model.generate_content(prompt)
        corrected_text = response.text.strip().strip("`").strip()
        print("Correction received.")
        return corrected_text
    except Exception as e:
        print(f"Error during Gemini correction: {e}")
        return None


def correct_transcript_with_openai(text_to_correct, model_name=None):
    model = model_name or "gpt-4o"
    prompt = create_correction_prompt(text_to_correct)
    try:
        print(f"Sending correction request to OpenAI API using {model}...")
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        corrected_text = response.choices[0].message.content.strip()
        print("Correction received.")
        return corrected_text
    except Exception as e:
        print(f"Error during OpenAI correction: {e}")
        return None


def correct_transcript_with_claude(text_to_correct, model_name=None):
    model = model_name or "claude-3-7-sonnet-20250219"
    prompt = create_correction_prompt(text_to_correct)
    try:
        print(f"Sending correction request to Claude API using {model} (streaming)...")
        client = anthropic.Anthropic()
        with client.messages.with_streaming_response.create(
            model=model,
            max_tokens=100000,
            temperature=0.0,
            stream = True,
            messages=[{"role": "user", "content": prompt}]
        ) as response:
            corrected_text = ""
            for chunk in response.iter_text():
                corrected_text += chunk
        print("Correction received.")
        return corrected_text.strip()
    except Exception as e:
        print(f"Error during Claude correction: {e}")
        return None


def summarize_transcript(text, provider="gemini", model_name=None):
    if provider == "gemini":
        return summarize_transcript_with_gemini(text, model_name)
    elif provider == "openai":
        return summarize_transcript_with_openai(text, model_name)
    elif provider == "claude":
        return summarize_transcript_with_claude(text, model_name)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def summarize_transcript_with_gemini(text, model_name=None):
    model = genai.GenerativeModel(model_name or 'gemma-3-27b-it')
    prompt = create_summary_prompt(text)
    try:
        print("Sending summarization request to Gemini API...")
        response = model.generate_content(prompt)
        summary_text = response.text.strip().strip("`").strip()
        print("Summary received.")
        return summary_text
    except Exception as e:
        print(f"Error during Gemini summarization: {e}")
        return None


def summarize_transcript_with_openai(text, model_name=None):
    model = model_name or "gpt-4.1-2025-04-14"
    prompt = create_summary_prompt(text)
    try:
        print(f"Sending summarization request to OpenAI API using {model}...")
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        summary_text = response.choices[0].message.content.strip()
        print("Summary received.")
        return summary_text
    except Exception as e:
        print(f"Error during OpenAI summarization: {e}")
        return None


def summarize_transcript_with_claude(text, model_name=None):
    model = model_name or "claude-3-5-sonnet-20240620"
    prompt = create_summary_prompt(text)
    try:
        print(f"Sending summarization request to Claude API using {model}...")
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=100000,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        summary_text = response.content[0].text.strip()
        print("Summary received.")
        return summary_text
    except Exception as e:
        print(f"Error during Claude summarization: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Transcript correction and summarization using AI models.")
    parser.add_argument("-i", "--input", required=True, help="Path to input transcript file.")
    parser.add_argument("-c", "--correct", action="store_true", help="Perform correction of the transcript.")
    parser.add_argument("-s", "--summarize", action="store_true", help="Perform summarization of the transcript.")
    parser.add_argument("--output", help="Path to save corrected transcript.")
    parser.add_argument("--summary", help="Path to save summary.")
    
    parser.add_argument("--provider", choices=["gemini", "openai", "claude"], default="gemini", 
                        help="AI provider to use (default: gemini)")
    parser.add_argument("--api-key", help="API key for the selected provider")
    parser.add_argument("--model", help="Model name to use with the selected provider")

    args = parser.parse_args()

    if not args.correct and not args.summarize:
        parser.print_help()
        print("\nError: You must specify at least one of --correct or --summarize.")
        return

    try:
        configure_api(provider=args.provider, api_key=args.api_key)
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            original_text = f.read()
        print(f"Loaded transcript from {args.input}")
    except Exception as e:
        print(f"Failed to read input file: {e}")
        return

    base_name = os.path.splitext(os.path.basename(args.input))[0]
    input_dir = os.path.dirname(args.input) or "."

    corrected_text = None

    if args.correct:
        corrected_text = correct_transcript(original_text, provider=args.provider, model_name=args.model)
        if corrected_text:
            out_path = args.output or os.path.join(input_dir, f"{base_name}_corrected.txt")
            try:
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(corrected_text)
                print(f"Corrected transcript saved to: {out_path}")
            except Exception as e:
                print(f"Failed to write corrected transcript: {e}")

    if args.summarize:
        text_to_summarize = corrected_text if corrected_text else original_text
        summary_text = summarize_transcript(text_to_summarize, provider=args.provider, model_name=args.model)
        if summary_text:
            sum_path = args.summary or os.path.join(input_dir, f"{base_name}_summary.txt")
            try:
                os.makedirs(os.path.dirname(sum_path), exist_ok=True)
                with open(sum_path, 'w', encoding='utf-8') as f:
                    f.write(summary_text)
                print(f"Summary saved to: {sum_path}")
            except Exception as e:
                print(f"Failed to write summary: {e}")


if __name__ == "__main__":
    main()