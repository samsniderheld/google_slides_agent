import json
import os
import uuid

def describe_element(element):
    """Return a human-readable description of a page element."""
    eid = element.get("objectId")
    
    if "shape" in element:
        shape_type = element["shape"].get("shapeType")
        # collect visible text
        text_runs = []
        for t in element["shape"].get("text", {}).get("textElements", []):
            if "textRun" in t:
                content = t["textRun"].get("content", "").strip()
                if content:
                    text_runs.append(content)
        text_preview = " | ".join(text_runs) if text_runs else "(no text)"
        return f"Shape ({shape_type}) [{eid}] → text: {text_preview}"
    
    elif "image" in element:
        url = element["image"].get("contentUrl", "(no url)")
        return f"Image [{eid}] → {url}"
    
    elif "line" in element:
        line_type = element["line"].get("lineType", "LINE")
        return f"Line [{eid}] → {line_type}"
    
    elif "table" in element:
        rows = element["table"].get("rows", 0)
        cols = element["table"].get("columns", 0)
        return f"Table [{eid}] → {rows} rows × {cols} cols"
    
    else:
        return f"Other element [{eid}]"



def build_duplicate_and_replace_requests(slide, new_slide_id=None):
    """
    Given a slide JSON object (from presentations().get(...)),
    return a batchUpdate request that:
      1. Duplicates the slide with a new slideId
      2. Replaces the text for each text shape
    
    Args:
        slide (dict): one item from presentation["slides"]
        new_slide_id (str, optional): custom id for the new slide. 
                                      Defaults to a generated id.
    Returns:
        dict: batchUpdate request body
    """
    original_slide_id = slide.get("objectId")
    if not new_slide_id:
        new_slide_id = f"NewSlide_{uuid.uuid4().hex[:8]}"  # unique-ish id

    requests = []
    text_lengths = []

    # 1. Duplicate the slide with a new ID
    requests.append({
        "duplicateObject": {
            "objectId": original_slide_id,
            "objectIds": {
                original_slide_id: new_slide_id
            }
        }
    })

    # 2. Walk through pageElements and create replaceAllText requests
    for element in slide.get("pageElements", []):
        if "shape" in element:
            texts = []
            for te in element["shape"].get("text", {}).get("textElements", []):
                if "textRun" in te:
                    content = te["textRun"].get("content", "").strip()
                    if content:
                        texts.append(content)

            for t in texts:
                # Replace each existing text with a placeholder or new content
                text_length = str(len(t))
                requests.append({
                    "replaceAllText": {
                        "containsText": {
                            "text": t,
                            "matchCase": False
                        },
                        # Here you can control what to replace it with:
                        "replaceText": "{CONVERT THE TEXT IDEA OR CONCEPT TO TEXT THAT AT MOST " + text_length +" CHARACTERS LONG}",
                        "pageObjectIds": [new_slide_id]
                    }
                })

                text_lengths.append(f"{text_length} char string")

    return {"requests": requests}, text_lengths


def generate_slide_summaries_string(input_directory="slide_templates"):
    """
    Reads JSON files in a directory, extracts slide type and description,
    and returns a concatenated string of the summaries.

    Args:
        input_directory (str): The path to the directory containing the slide template files.

    Returns:
        str: A string containing concatenated slide type and description for each file.
             Returns an empty string if an error occurs or no files are processed.
    """
    slide_summaries = []
    try:
        for filename in os.listdir(input_directory):
            if filename.endswith(".txt"):  # Assuming the files are text files containing JSON
                file_path = os.path.join(input_directory, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as infile:
                        content = infile.read()
                        json_object = json.loads(content)

                        slide_info = json_object.get("slide", {})
                        slide_type = slide_info.get("slide_type", "N/A")
                        slide_description = slide_info.get("slide_description", "N/A")
                        text_sections = ", ".join(slide_info.get("text_sections", []))
                        slide_summaries.append(f"{slide_type}: {slide_description}: {text_sections}")

                except json.JSONDecodeError:
                    print(f"Error: Could not decode JSON from {filename}")
                except Exception as e:
                    print(f"An error occurred while processing {filename}: {e}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "" # Return empty string in case of directory error

    return "\n\n".join(slide_summaries)

# Example usage (optional, can be removed if only the function is needed):
# summaries_string = generate_slide_summaries_string()
# print(summaries_string)


def create_yaml_file(name: str, system_prompt: str, output_path: str) -> None:
    """
    Create a new YAML file with name and system_prompt keys.
    
    Args:
        name (str): Name for the configuration
        system_prompt (str): System prompt content
        output_path (str): Path where the YAML file should be created
    """
    # Create YAML content manually to ensure proper formatting
    yaml_content = f"""name: {name}\nsystem_prompt: |{system_prompt.replace(chr(10), chr(10) + '  ')}
    """
    
    with open(output_path, 'w') as file:
        file.write(yaml_content)
