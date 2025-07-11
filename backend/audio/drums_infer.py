from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
import torch, librosa, numpy as np


def infer_drums(drums_file_path, confidence_threshold:float=0.7, model:str="yojul/wav2vec2-base-one-shot-hip-hop-drums-clf"):
    """
    Infer drum events from an audio file using a pre-trained Wav2Vec2 model.
    
    Args:
        drums_path (str): Path to the audio file containing drum sounds.
        
    Returns:
        list: A list of dictionaries with inferred drum events.
    """
    if not drums_file_path:
        return []
    
    print(f"🥁 Inferring drums from {drums_file_path}...")

    # load model and feature extractor
    model_name = model
    feat = Wav2Vec2FeatureExtractor.from_pretrained(model_name)
    model = Wav2Vec2ForSequenceClassification.from_pretrained(model_name)

    # load audio file
    y, sr = librosa.load(drums_file_path, sr=16000, mono=True)
    window, hop = int(0.1*sr), int(0.05*sr)
    events = []

    # process audio in chunks
    for start in range(0, len(y)-window, hop):
        chunk = y[start:start+window]
        inputs = feat(chunk, sampling_rate=sr, return_tensors="pt")
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=-1).squeeze().cpu().numpy()
        label = model.config.id2label[np.argmax(probs)]
        conf = float(np.max(probs))
        if conf > confidence_threshold:  # tune down if needed
            events.append({"time": (start+window/2)/sr, "type": label, "confidence": conf})

    # group events by type
    if not events:
        return []
    
    drums_events = []
    unique_types = set(e['type'] for e in events)
    for t in unique_types:
        drums_events.append({
            "type": t,
            "time": [(e['time'], e['confidence']) for e in events if e['type'] == t]
            })
    return drums_events


## Example usage:
if __name__ == "__main__":
    drums_file = "/home/darkangel/ai-light-show/songs/born_slippy.mp3"
    print(f"Inferring drums from {drums_file}...")
    results = infer_drums(drums_file)
    print("Inferred drum events:")
    for event in results:
        print(event)