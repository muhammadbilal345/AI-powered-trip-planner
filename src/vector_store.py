import faiss
import json
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from typing import List, Dict

class VectorStore:
    def __init__(self, dimension: int, index_path: str = "trip_plan_index.faiss", metadata_path: str = "trip_plan_metadata.json", threshold: float = 1.3):
        self.dimension: int = dimension
        self.index_path: str = index_path
        self.metadata_path: str = metadata_path
        self.threshold: float = threshold
        self.model: SentenceTransformer = SentenceTransformer('all-MiniLM-L6-v2')  # Model producing 384-dimensional embeddings
        
        # Load or initialize the FAISS index
        if os.path.exists(self.index_path):
            self.index: faiss.Index = faiss.read_index(self.index_path)
        else:
            self.index: faiss.Index = faiss.IndexFlatL2(dimension)
        
        # Load or initialize metadata
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r") as f:
                self.metadata: List[Dict] = json.load(f)
        else:
            self.metadata: List[Dict] = []

    def save(self) -> None:
        # Save the FAISS index to disk
        faiss.write_index(self.index, self.index_path)
        
        # Save the metadata to disk
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f)

    def add_plan(self, trip_plan: str, metadata: Dict) -> None:
        # Generate the embedding for the trip plan
        embedding: np.ndarray = self.model.encode(f"{metadata['location']} {metadata['date_range']} {trip_plan}")
        print(f"Embedding shape: {embedding.shape}")

        if embedding.shape[0] != self.dimension:
            raise ValueError(f"Embedding dimension {embedding.shape[0]} does not match index dimension {self.dimension}")
        
        self.index.add(np.array([embedding]))  # Add embedding to FAISS index
        
        # Ensure the trip plan is included in the metadata
        metadata['trip_plan'] = trip_plan
        self.metadata.append(metadata)

        # Save the index and metadata
        self.save()

    def search_plan(self, query: str, top_k: int = 1) -> List[Dict]:
        query_embedding: np.ndarray = self.model.encode(query).reshape(1, -1)
        distances: np.ndarray
        indices: np.ndarray
        distances, indices = self.index.search(query_embedding, top_k)
        return [self.metadata[i] for i in indices[0]]
    
    def retrieve_trip_plan(self, location: str) -> str:
        query_embedding: np.ndarray = self.model.encode(f"{location}").reshape(1, -1)
        distances: np.ndarray
        indices: np.ndarray
        distances, indices = self.index.search(query_embedding, k=1)

        # Debugging output to check what's being returned
        print(f"Distances: {distances}")
        print(f"Indices: {indices}")

        # Check if the closest match is within the acceptable threshold
        if indices[0][0] >= 0 and distances[0][0] < self.threshold:
            return self.metadata[indices[0][0]]['trip_plan']
        else:
            # Return a message indicating no plan was found
            raise IndexError("No matching trip plan found.")

