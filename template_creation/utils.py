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
