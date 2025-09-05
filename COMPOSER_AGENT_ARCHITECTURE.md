# Composer Agent Architecture

This document outlines how to design an image composer agent that collaborates with a copywriter agent to create on-brand visual assets.

## Inputs
- **Brand document ID** – resolves fonts, colors, and logos.
- **Post plan ID** – defines number of images, aspect ratios, and sourcing preferences.
- **Copywriter output** – for each image: description, overlay text, and whether to search or generate the base image.

## Agent Workflow
1. **Fetch context**
   - Load brand and post plan documents using their IDs.
2. **Gather base images**
   - If the copywriter requests a search, call image search APIs or internal stores.
   - If generation is requested, call a model such as Stable Diffusion or DALL·E.
3. **Compose candidate previews**
   - Build a list of layers (image and text) describing position, size, rotation, opacity, font, and color.
   - Call the Pillow-based `compose_image` function to render one or more PNG previews.
4. **Self-review and refine**
   - Generate variations by tweaking prompts, seeds, or layer properties.
   - Score each candidate using CLIP similarity, brand heuristics, or aesthetic models.
   - Keep the best-scoring preview or loop until quality thresholds are met.
5. **Collaborate and iterate**
   - Return the chosen preview to the copywriter agent.
   - Accept adjustments to layer properties or regeneration requests and re-compose until approved.
6. **Finalize and store**
   - Save approved images to blob storage and collect their URLs.
   - Attach the URLs to the post for publishing (single image or carousel).

## Composition Function Guidelines
```python
@dataclass
class ImageLayer:
    type: Literal["image", "text"]
    source: str | None
    prompt: str | None
    position: tuple[int, int]
    size: tuple[int, int] | None
    rotation: float | None
    opacity: float = 1.0
    text: str | None
    font_name: str | None
    font_size: int | None
    color: str | None
    stroke_color: str | None
    stroke_width: int | None
```
- Layers allow multiple images and text blocks with independent styling.
- The function should output a base64-encoded PNG for easy transport.

## Tools to Register
- `search_images(query, source, brand_id)`
- `generate_image(prompt, brand_id)`
- `compose_image(composition_request)`
- `rate_image(image, prompt, brand_id)`
- `refine_prompt(prompt, feedback)`
- `save_to_blob(image_bytes, path)`

These tools enable the agent to retrieve assets, generate previews, critique results, and store approved images.

## Best Practices for Creative Image Generation
- Preserve metadata for each iteration (prompts, seeds, scores) to allow reproducibility and learning.
- Produce multiple candidates and track scores to encourage exploration.
- Use asynchronous generation to explore variations in parallel.
- Allow agents to provide structured critiques on composition and color balance to guide prompt refinement.
