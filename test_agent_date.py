
import argparse
from google.cloud import storage
import vertexai
from vertexai.preview import reasoning_engines

def test_date_extraction(project, location, engine_resource, video_id, publish_date):
    vertexai.init(project=project, location=location)
    agent = reasoning_engines.ReasoningEngine(engine_resource)
    
    print(f"Testing Agent on video {video_id} (Expected Date: {publish_date})...")
    
    prompt = (
        f"Retrieve the transcript for video_id={video_id}. "
        f"The video was published on {publish_date}. "
        f"TASK: Identify the publish date of this video from the transcript content or the metadata provided. "
        f"OUTPUT: Return ONLY the date in YYYY-MM-DD format. Do not return any other text."
    )
    
    response = agent.query(prompt=prompt)
    print("\n--- Agent Response ---")
    print(response)
    print("----------------------")

if __name__ == "__main__":
    test_date_extraction(
        project="nate-digital-twin",
        location="us-central1",
        engine_resource="projects/134885012683/locations/us-central1/reasoningEngines/1630571345945296896",
        video_id="xZX4KHrqwhM",
        publish_date="2025-06-23"
    )
