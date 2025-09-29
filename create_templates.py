import argparse
import json
import json_repair
import os
import sys

from googleapiclient.discovery import build
from google.auth import default

from agents.base_agent import BaseAgent
from template_creation.utils import *

def main():
    parser = argparse.ArgumentParser(description="Create slide templates from Google Slides presentation")
    parser.add_argument("--presentation_id", 
                       default="1kKzgzXhb4cc_Dn7z1lxui8sIfCan4xqs_Y-xHgzU0vk",
                       help="Google Slides presentation ID")
    parser.add_argument("--output_dir", 
                       default="slide_templates",
                       help="Output directory for slide templates (default: slide_templates)")
    parser.add_argument("--config_file", 
                       default="config_files/template_creator.yaml",
                       help="Path to document creator config file")
    parser.add_argument("--schema_path", 
                       default="config_files/template_schema.yaml",
                       help="Path to slide document schema file")
    parser.add_argument("--llm", 
                       default="openai",
                       choices=["openai", "gemini"],
                       help="LLM provider to use (default: openai)")
    parser.add_argument("--model", 
                       help="Specific model to use for the LLM provider")
    parser.add_argument("--create_yaml",
                        action="store_true",
                        help="Creates a new deck creative yaml using the latest templates")
    parser.add_argument("--deck_creative_yaml_path", 
                       default="config_files/deck_creative.yaml",
                       help="Path to slide document schema file")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize Google Slides API
    creds, _ = default()
    slides = build("slides", "v1", credentials=creds)
    
    # Initialize document creator agent
    agent_kwargs = {
        "config_file": args.config_file,
        "llm": args.llm,
        "schema_path": args.schema_path
    }
    if args.model:
        agent_kwargs["model"] = args.model
        
    document_creator = BaseAgent(**agent_kwargs)
    
    # Fetch the presentation JSON
    try:
        pres = slides.presentations().get(
            presentationId=args.presentation_id,
        ).execute()
    except Exception as e:
        print(f"Error fetching presentation: {e}")
        sys.exit(1)
    
    print(f"Processing {len(pres['slides'])} slides...")
    
    for i, slide in enumerate(pres["slides"], start=1):
        slide_id = slide.get("objectId")
        output = []
        output.append(f"# Slide {i}\n")
        output.append(f"# slideId: {slide_id}\n")
    
        elements = slide.get("pageElements", [])
        if not elements:
            output.append("No page elements on this slide.\n")
        else:
            for j, element in enumerate(elements, start=1):
                output.append(f"{j}. {describe_element(element)}")
    
        slide_content = "\n".join(output)
    
        try:
            slide_document = document_creator.basic_api_call_structured(slide_content)
            slide_document_json = json_repair.loads(slide_document.model_dump_json(indent=2))
        except Exception as e:
            print(f"Error processing slide {i}: {e}")
            continue
    
        new_json_object, text_sections = build_duplicate_and_replace_requests(slide)
    
        slide_document_json["slide"]["json_object"] = new_json_object
        slide_document_json["slide"]["text_sections"] = text_sections
    
        print(f"Processed slide {i}: {slide_document_json['slide']['slide_type']}")
    
        new_type_name = slide_document_json["slide"]["slide_type"].replace(" ","_").replace("/","").lower()
        slide_document_json["slide"]["slide_type"] = new_type_name
        file_name = os.path.join(args.output_dir, f"{new_type_name}.txt")
    
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(json.dumps(slide_document_json, indent=2))
            
    print(f"Template creation complete. Files saved to {args.output_dir}/")

    if args.create_yaml:

        summaries_string = generate_slide_summaries_string()

        print(summaries_string)

        #todo: make this less ugly
        deck_creative_system_prompt = f"""
You are a deck_creative agent. Your job is to take a creative concept and output a outline of the creative pitch deck.
For each slide specifiy one of the following slide types and create text the matches the specified text lengths:

{summaries_string}

IMPORTANT: FOLLOW THE ORDER AND CHARACTER LENGHT OF EACH SLIDE TYPE EXACTLY!!!
IMPORTANT: USE THE DESCRIPTION OF THE SLIDES AS THE BASIS FOR HOW YOU FILL IN THE SLIDE. 

"""

        create_yaml_file(name="deck_creative", system_prompt=deck_creative_system_prompt,output_path=args.deck_creative_yaml_path)

    print(f"Deck creative yaml updates. Files saved to {args.deck_creative_yaml_path}")

if __name__ == "__main__":
    main()
    
