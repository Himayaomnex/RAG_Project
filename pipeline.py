import os
os.environ["HF_HUB_OFFLINE"] = "1"
import re
import uuid
import docx
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchText, MatchValue
from sentence_transformers import SentenceTransformer, util
import shelve
import hashlib
import json
import urllib.request
import urllib.error
import torch
from dotenv import load_dotenv
from transcript_normalizer import (
    reattribute_crosstalk_turn,
    normalize_speaker_name,
    clean_audio_artifacts,
    is_mentor_speaking_pattern
)
load_dotenv()


FILE_DATE_MAP = {
    'AI_ML- Training .docx': '2 July 2026',
    'AI_ML- Training  (1).docx': '3 July 2026',
    'AI_ML- Training  (2).docx': '8 July 2026',
    'AI_ML- Training  (3).docx': '10 July 2026',
    'AI_ML- Training  (4).docx': '13 July 2026',
    'AI_ML- Training  (5).docx': '13 July 2026',
    'AI_ML- Training  (6).docx': '14 July 2026',
    'AI_ML- Training  (7).docx': '15 July 2026',
    'AI_ML- Training  (8).docx': '16 July 2026',
    'AI_ML- Training  (9).docx': '17 July 2026',
    'AI_ML- Training  (10).docx': '20 July 2026',
    'AI_ML- Training  (11).docx': '21 July 2026',
    'AI_ML- Training  (12).docx': '21 July 2026',
    'AI_ML- Training  (13).docx': '22 July 2026',
    'AI_ML- Training  (14).docx': '23 July 2026',
    'AI_ML- Training  (15).docx': '24 July 2026',
    'AI_ML- Training  (16).docx': '27 July 2026',
    'AI_ML- Training  (17).docx': '28 July 2026',
    'AI_ML- Training  (18).docx': '29 July 2026',
    'AI_ML- Training  (19).docx': '30 July 2026',
    'AI_ML- Training  (20).docx': '31 July 2026',
    'AI_ML- Training  (21).docx': '4 August 2026',
}

class CachedEmbeddingModel:
    """Wraps SentenceTransformer with a local disk cache to prevent slow re-embedding."""
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emb_cache")
        
    def encode(self, texts, convert_to_tensor=False):
        is_single = isinstance(texts, str)
        text_list = [texts] if is_single else texts
        
        embeddings = []
        needs_encoding = []
        needs_encoding_idx = []
        
        try:
            # Use writeback=False to minimize lock contention time
            with shelve.open(self.cache_file, flag='c', writeback=False) as cache:
                for i, t in enumerate(text_list):
                    h = hashlib.md5(t.encode('utf-8')).hexdigest()
                    if h in cache:
                        embeddings.append(cache[h])
                    else:
                        embeddings.append(None)
                        needs_encoding.append(t)
                        needs_encoding_idx.append(i)
                        
                if needs_encoding:
                    fresh_embs = self.model.encode(needs_encoding).tolist()
                    for idx, emb in zip(needs_encoding_idx, fresh_embs):
                        embeddings[idx] = emb
                        cache[hashlib.md5(text_list[idx].encode('utf-8')).hexdigest()] = emb
        except Exception as e:
            # Fallback to direct encoding if shelve is locked or has access error
            print(f"  - [Cache Warning]: shelve access error: {e}. Falling back to direct model encoding...")
            embeddings = self.model.encode(text_list).tolist()
            
        if convert_to_tensor:
            return torch.tensor(embeddings)
        return embeddings[0] if is_single else embeddings

class Sentence:
    def __init__(self, text, speaker, page, file_path):
        self.text = text
        self.speaker = speaker
        self.page = page
        self.file_path = file_path

class SemanticTranscriptParser:
    """
    Parses .docx transcripts into sentences and uses Semantic Chunking (Topic Shifts)
    """
    def __init__(self, directory="Downloads", dense_model=None):
        if not os.path.isabs(directory):
            self.directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), directory)
        else:
            self.directory = directory
            
        if dense_model:
            self.model = dense_model
        else:
            print("Loading Embedding Model for Semantic Chunking...")
            self.model = CachedEmbeddingModel("all-MiniLM-L6-v2")
        
    def parse_all(self):
        all_chunks = []
        if not os.path.exists(self.directory):
            print(f"Warning: Directory {self.directory} does not exist.")
            return all_chunks
            
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".docx") and not file.startswith("~"):
                    file_path = os.path.join(root, file)
                    all_chunks.extend(self.parse_document(file_path))
        return all_chunks

    def _build_chunk(self, sentence_objs, chunk_id, date, file_path, reason="Document End"):
        full_text = ""
        speakers = set()
        pages = set()
        
        last_speaker = None
        for s in sentence_objs:
            speakers.add(s.speaker)
            pages.add(s.page)
            if s.speaker != last_speaker:
                full_text += f"\n{s.speaker}: {s.text} "
                last_speaker = s.speaker
            else:
                full_text += f"{s.text} "
                
        page_list = sorted(list(pages))
        if len(page_list) > 1:
            page_str = f"{page_list[0]}-{page_list[-1]}"
        else:
            page_str = str(page_list[0]) if page_list else "1"
            
        return {
            "text": full_text.strip(),
            "speaker": ", ".join(sorted(list(speakers))[:3]) + ("..." if len(speakers) > 3 else ""),
            "date": date,
            "chunk_id": chunk_id,
            "page": page_str,
            "source_file": os.path.basename(file_path),
            "cut_reason": reason
        }

    def parse_document(self, path):
        doc = docx.Document(path)
        filename = os.path.basename(path)
        date = self.extract_date(doc, filename)
        
        all_sentences = []
        current_speaker = "Unknown"
        current_page = 1
        page_char_count = 0
        
        for p in doc.paragraphs:
            lines = p.text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                header_match = re.match(r"^([a-zA-Z\s\.]+)\s+\d{1,2}:\d{2}", line)
                if header_match and len(line.split()) < 15: 
                    current_speaker = normalize_speaker_name(header_match.group(1).strip())
                    continue
                
                # Split line into sentences
                sentences = re.split(r'(?<=[.!?])\s+', line)
                for s in sentences:
                    s = s.strip()
                    if s:
                        # FILTER TRANSCRIPTION NOISE
                        noise_phrases = ["stopped transcription", "started transcription", "joined the meeting", "left the meeting"]
                        is_noise = any(phrase in s.lower() for phrase in noise_phrases)
                        if is_noise:
                            continue
                        
                        # PRE-CHUNKING RE-ATTRIBUTION & ENTITY NORMALIZATION
                        real_speaker, clean_s = reattribute_crosstalk_turn(current_speaker, s)
                        if clean_s:
                            all_sentences.append(Sentence(clean_s, real_speaker, current_page, path))
                            page_char_count += len(clean_s)

                
                if page_char_count > 2500:
                    current_page += 1
                    page_char_count = 0
                    
        chunks = []
        i = 0
        chunk_id = 0
        target_char_limit = 1200
        
        print(f"Applying Semantic Chunking to {filename} ({len(all_sentences)} sentences)...")
        
        while i < len(all_sentences):
            current_chars = 0
            candidate_idx = i
            
            while candidate_idx < len(all_sentences) and current_chars < target_char_limit:
                current_chars += len(all_sentences[candidate_idx].text)
                candidate_idx += 1
                
            if candidate_idx == len(all_sentences):
                chunks.append(self._build_chunk(all_sentences[i:candidate_idx], chunk_id, date, path, "Document End"))
                break
                
            start_window = max(i + 1, candidate_idx - 30)
            end_window = min(len(all_sentences) - 1, candidate_idx + 30)
            
            if start_window >= end_window:
                best_cut = candidate_idx
                reason = "Target Size Fallback (Window too small)"
            else:
                window_sentences = all_sentences[start_window:end_window+1]
                texts = [s.text for s in window_sentences]
                
                embeddings = self.model.encode(texts, convert_to_tensor=True)
                
                min_sim = 1.0
                best_cut = candidate_idx
                
                for j in range(len(embeddings) - 1):
                    sim = util.cos_sim(embeddings[j], embeddings[j+1]).item()
                    if sim < min_sim:
                        min_sim = sim
                        best_cut = start_window + j + 1
                        
                reason = f"Topic Shift Detected (Similarity: {min_sim:.3f})"
                
            chunks.append(self._build_chunk(all_sentences[i:best_cut], chunk_id, date, path, reason))
            i = best_cut
            chunk_id += 1
            
        return chunks

    def extract_date(self, doc, filename):
        if filename in FILE_DATE_MAP:
            return FILE_DATE_MAP[filename]
        date_pattern = r"\b(\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b"
        for p in doc.paragraphs:
            match = re.search(date_pattern, p.text, re.IGNORECASE)
            if match:
                return match.group(1)
        match = re.search(date_pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1)
        return "22 July 2026"


_GLOBAL_DENSE_MODEL = None

def get_dense_model():
    global _GLOBAL_DENSE_MODEL
    if _GLOBAL_DENSE_MODEL is None:
        _GLOBAL_DENSE_MODEL = CachedEmbeddingModel("all-MiniLM-L6-v2")
    return _GLOBAL_DENSE_MODEL

_vector_db_instance = None

class VectorDatabase:
    def __init__(self, collection_name="teams_dense_collection"):
        qdrant_url = os.getenv("QDRANT_URL")
        if qdrant_url:
            print(f"Connecting to Qdrant Server at {qdrant_url}...")
            self.client = QdrantClient(url=qdrant_url)
        else:
            storage_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qdrant_storage")
            try:
                self.client = QdrantClient(path=storage_path)
            except Exception as e:
                print("  - [Qdrant Lock Notice]: Using in-memory fallback client...")
                self.client = QdrantClient(location=":memory:")


        self.collection_name = collection_name
        self.dense_model = get_dense_model()
        self.setup_collection()




        
    def setup_collection(self):
        if not self.client.collection_exists(self.collection_name):
            print(f"Creating Qdrant collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": VectorParams(size=384, distance=Distance.COSINE)
                }
            )

    def insert_chunks(self, chunks):
        print(f"Embedding and inserting {len(chunks)} chunks into Qdrant...", flush=True)
        texts = [c["text"] for c in chunks]
        dense_vecs = self.dense_model.encode(texts)
        points = []
        for c, vec in zip(chunks, dense_vecs):
            if hasattr(vec, 'tolist'):
                vec = vec.tolist()
            point_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=point_id,
                payload=c,
                vector={
                    "dense": vec
                }
            ))
            
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )


def get_vector_db():
    global _vector_db_instance
    if _vector_db_instance is None:
        import time
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                _vector_db_instance = VectorDatabase()
                break
            except Exception as e:
                if attempt < max_attempts - 1:
                    time.sleep(0.8)
                else:
                    raise e
    return _vector_db_instance




class CustomMeetingReranker:
    """A highly specialized reranker tuned specifically for meeting data."""
    def rerank(self, query: str, results):
        query_lower = query.lower()
        stop_words = {"what", "is", "the", "difference", "between", "an", "and", "according", "to", "did", "say", "about", "how", "are", "you"}
        keywords = [w for w in re.findall(r'\b\w+\b', query_lower) if w not in stop_words and len(w) > 3]
        
        for res in results:
            score = res.score
            
            # 1. Speaker Match Boost
            chunk_speaker = res.payload.get("speaker", "").lower()
            if any(s in query_lower and s in chunk_speaker for s in ["siddharth", "dakshinya", "himaya", "ganesh"]):
                score += 0.5
                
            # 2. Date Match Boost
            chunk_date = res.payload.get("date", "").lower()
            if chunk_date and chunk_date != "unknown date" and chunk_date in query_lower:
                score += 0.5
                
            # 3. Topic Density Match
            chunk_text = res.payload.get("text", "").lower()
            keyword_matches = sum(1 for k in keywords if k in chunk_text)
            score += (keyword_matches * 0.05)
            
            res.score = score
            
        return sorted(results, key=lambda x: x.score, reverse=True)


class DenseRetriever:
    def __init__(self, db: VectorDatabase = None):
        if db is None:
            db = VectorDatabase()
        self.db = db
        print("Loading Custom Meeting Reranker...")
        self.reranker = CustomMeetingReranker()
        
    def retrieve(self, query: str, top_k=10, rerank_top_k=4):
        must_conditions = []
        
        known_speakers = ["Siddharth", "Ganesh", "Dakshinya", "Himaya"]
        for speaker in known_speakers:
            if speaker.lower() in query.lower():
                must_conditions.append(
                    FieldCondition(key="speaker", match=MatchText(text=speaker))
                )
                
        date_pattern = r"\b(\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b"
        date_match = re.search(date_pattern, query, re.IGNORECASE)
        if date_match:
            must_conditions.append(
                FieldCondition(key="date", match=MatchValue(value=date_match.group(1)))
            )
            
        query_filter = Filter(must=must_conditions) if must_conditions else None

        dense_vec = self.db.dense_model.encode(query)
        if hasattr(dense_vec, 'tolist'):
            dense_vec = dense_vec.tolist()
        
        try:
            results = self.db.client.query_points(
                collection_name=self.collection_name if hasattr(self, 'collection_name') else self.db.collection_name,
                query=dense_vec,
                query_filter=query_filter,
                using="dense",
                limit=top_k
            ).points
        except Exception:
            # Fallback scroll search if query_points API differs
            results = []
            pts, _ = self.db.client.scroll(collection_name=self.db.collection_name, limit=1000)
            for p in pts:
                payload = p.payload if hasattr(p, 'payload') else {}
                txt = payload.get("text", "")
                sim = float(util.cos_sim(torch.tensor(dense_vec), torch.tensor(self.db.dense_model.encode(txt))).item())
                
                class MockPoint:
                    def __init__(self, p_id, p_load, p_score):
                        self.id = p_id
                        self.payload = p_load
                        self.score = p_score
                        
                results.append(MockPoint(p.id if hasattr(p, 'id') else uuid.uuid4(), payload, sim))
            results.sort(key=lambda x: x.score, reverse=True)
            results = results[:top_k]
            
        if not results:
            return []
            
        results = self.reranker.rerank(query, results)
        return results[:rerank_top_k]

    # --- THE 4 EXPLICIT RETRIEVAL PIPELINE MODES ---

    def retrieve_p1_scroll_reranker(self, query: str, top_k: int = 15, rerank_top_k: int = 4):
        """Pipeline 1 (P1): Full-collection Scroll + Custom Reranker (Recommended Production Mode)"""
        return self.retrieve(query=query, top_k=top_k, rerank_top_k=rerank_top_k)

    def retrieve_p2_scroll_scan(self, query: str, top_k: int = 35):
        """Pipeline 2 (P2): Expanded Recall Scroll API Scan (Raw Cosine Order, K=35)"""
        must_conditions = self._build_metadata_filters(query)
        query_filter = Filter(must=must_conditions) if must_conditions else None
        dense_vec = self.db.dense_model.encode(query)
        if hasattr(dense_vec, 'tolist'):
            dense_vec = dense_vec.tolist()
            
        try:
            results = self.db.client.query_points(
                collection_name=self.db.collection_name,
                query=dense_vec,
                query_filter=query_filter,
                using="dense",
                limit=top_k
            ).points
        except Exception:
            results = []
            
        return results[:top_k]

    def retrieve_p3_doc_balanced(self, query: str, top_k: int = 15, max_per_doc: int = 2):
        """Pipeline 3 (P3): Low-Latency Native HNSW Doc-Balanced Search (Capped at 2 chunks per doc)"""
        must_conditions = self._build_metadata_filters(query)
        query_filter = Filter(must=must_conditions) if must_conditions else None
        dense_vec = self.db.dense_model.encode(query)
        if hasattr(dense_vec, 'tolist'):
            dense_vec = dense_vec.tolist()

        try:
            raw_pts = self.db.client.query_points(
                collection_name=self.db.collection_name,
                query=dense_vec,
                query_filter=query_filter,
                using="dense",
                limit=top_k * 2
            ).points
        except Exception:
            raw_pts = []

        doc_counts = {}
        balanced_results = []
        for pt in raw_pts:
            payload = pt.payload if hasattr(pt, 'payload') else {}
            src = payload.get("source_file", "unknown")
            doc_counts[src] = doc_counts.get(src, 0) + 1
            if doc_counts[src] <= max_per_doc:
                balanced_results.append(pt)
            if len(balanced_results) >= top_k:
                break
        return balanced_results

    def retrieve_p4_full_corpus_mapreduce(self, query: str) -> List[Dict[str, Any]]:
        """Pipeline 4 (P4): Broad Full-Corpus XML Map-Reduce Ingestion (Ingests 100% of transcripts in 1 call)"""
        pts, _ = self.db.client.scroll(collection_name=self.db.collection_name, limit=1000)
        full_xml_chunks = []
        for p in pts:
            payload = p.payload if hasattr(p, 'payload') else {}
            full_xml_chunks.append({
                "text": f"<document name=\"{payload.get('source_file', 'doc')}\" date=\"{payload.get('date', 'date')}\">\n{payload.get('text', '')}\n</document>",
                "speaker": payload.get("speaker", "Team"),
                "date": payload.get("date", "Unknown Date"),
                "page": str(payload.get("page", "1")),
                "source_file": payload.get("source_file", "doc"),
                "score": 1.0
            })
        return full_xml_chunks

    def _build_metadata_filters(self, query: str) -> List[FieldCondition]:
        must_conditions = []
        known_speakers = ["Siddharth", "Ganesh", "Dakshinya", "Himaya"]
        for speaker in known_speakers:
            if speaker.lower() in query.lower():
                must_conditions.append(FieldCondition(key="speaker", match=MatchText(text=speaker)))
        date_pattern = r"\b(\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b"
        date_match = re.search(date_pattern, query, re.IGNORECASE)
        if date_match:
            must_conditions.append(FieldCondition(key="date", match=MatchValue(value=date_match.group(1))))
        return must_conditions



def ensure_pipeline_initialized():
    db = get_vector_db()
    try:

        collection_info = db.client.get_collection(db.collection_name)
        has_data = collection_info.points_count > 0
    except Exception:
        has_data = False

    if not has_data:
        print("[Pipeline]: Ingesting transcripts from Downloads...")
        parser = SemanticTranscriptParser(directory="Downloads", dense_model=db.dense_model)
        chunks = parser.parse_all()
        if chunks:
            db.insert_chunks(chunks)
            print(f"[Pipeline]: Ingested {len(chunks)} chunks into Qdrant collection '{db.collection_name}'.")
    return db

if __name__ == "__main__":
    db = ensure_pipeline_initialized()
    retriever = DenseRetriever(db)
    res = retriever.retrieve("What did Ganesh discuss about vector database?", top_k=5, rerank_top_k=3)
    print(f"Retrieved {len(res)} chunks.")
    for r in res:
        print(f"- [{r.payload.get('date')} | {r.payload.get('speaker')}]: {r.payload.get('text')[:100]}...")
