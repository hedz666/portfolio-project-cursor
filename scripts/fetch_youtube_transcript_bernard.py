import re
import os
from collections import Counter
from youtube_transcript_api import YouTubeTranscriptApi

# Konfigurasi
VIDEO_ID = "2Ldce9z_ZuM"
URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"

# Path disesuaikan agar tetap bisa dijalankan dari dalam folder /scripts/
# Kode ini akan mencari folder 'research' satu tingkat di atas folder 'scripts'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(BASE_DIR, "research", "youtube-transcripts", "bernard-huang.md")

def clean(s: str) -> str:
    s = (s or "").replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def sentences(text: str):
    # Memisahkan berdasarkan tanda baca akhir kalimat
    parts = re.split(r"(?<=[.!?])\s+", text)
    for p in parts:
        p = clean(p)
        if len(p) < 45: 
            continue
        yield p

STOP = set("a an and are as at be but by for from has have i if in into is it its of on or our so that the their then there these they this to was we what when who why will with you your".split())

def keywords(text: str):
    toks = re.findall(r"[A-Za-z][A-Za-z']{2,}", text.lower())
    return [t for t in toks if t not in STOP]

def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s//60:02d}:{s%60:02d}"

def section_title(bucket_items) -> str:
    text = " ".join(clean(x.get("text", "")) for x in bucket_items)
    toks = [t for t in keywords(text) if len(t) > 3]
    common = [w for w, _ in Counter(toks).most_common(4)]
    if not common:
        return "Discussion"
    # Merapikan istilah teknis agar kapitalisasi benar (SEO, AI, dll)
    return " · ".join(w.upper() if w in {"seo", "aeo", "llm", "ai"} else w.capitalize() for w in common[:3])

def main():
    print(f"Fetching transcript for: {VIDEO_ID}...")
    
    try:
        # Perbaikan: Memanggil langsung dari Class, bukan instance
        items = YouTubeTranscriptApi.get_transcript(VIDEO_ID, languages=["en", "en-US"])
    except Exception as e:
        print(f"Language preference failed, trying default... ({e})")
        items = YouTubeTranscriptApi.get_transcript(VIDEO_ID)

    full_text = " ".join(clean(x.get("text", "")) for x in items)
    kw_freq = Counter(keywords(full_text))

    def score_sent(s: str) -> float:
        toks = keywords(s)
        if not toks: return 0.0
        # Mencari kalimat berbobot untuk 'Key Takeaways'
        return sum(kw_freq[t] for t in toks) / (1 + 0.05 * len(toks))

    cands = [(score_sent(s), s) for s in sentences(full_text)]
    cands.sort(reverse=True, key=lambda x: x[0])

    takeaways = []
    seen = set()
    for _, s in cands:
        sig = re.sub(r"[^a-z]+", "", s.lower())[:100]
        if sig in seen: continue
        seen.add(sig)
        # Membersihkan filler words di awal kalimat
        s2 = re.sub(r"^(so|and|but|now|okay|right|basically|actually)\s+", "", s, flags=re.I)
        takeaways.append(s2)
        if len(takeaways) >= 7: break

    # Mengelompokkan transcript per 2 menit agar enak dibaca
    window = 120
    buckets = {}
    for x in items:
        t = float(x.get("start", 0.0))
        buckets.setdefault(int(t // window), []).append(x)

    # Membangun struktur Markdown
    md = []
    md.append(f"# Bernard Huang — AEO Playbook (Analysis)")
    md.append("")
    md.append(f"- **Source**: [YouTube Video]({URL})")
    md.append("- **Focus**: AI Engine Optimization, LLM, and Search Trends 2026")
    md.append("")
    md.append("---")
    
    # BAGIAN KEY TAKEAWAYS (Gaya McDowell: Tebal di depan)
    md.append("\n## Key Takeaways")
    for t in takeaways:
        words = t.split()
        if len(words) > 2:
            label = " ".join(words[:2]).capitalize()
            content = " ".join(words[2:])
            md.append(f"- **{label}**: {content}")
        else:
            md.append(f"- {t}")

    md.append("\n---")
    
    # BAGIAN TRANSCRIPT (Gaya McDowell: Paragraf bersih per section)
    md.append("\n## Transcript")
    for b in sorted(buckets.keys()):
        bucket_items = buckets[b]
        start_ts = fmt_ts(bucket_items[0].get("start", 0.0))
        title = section_title(bucket_items)
        
        md.append(f"\n### {start_ts} — {title}")
        paragraph = " ".join(clean(x.get("text", "")) for x in bucket_items)
        md.append(paragraph)

    # Memastikan folder tujuan ada sebelum menulis file
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md).strip())

    print("-" * 30)
    print(f"SUCCESS!")
    print(f"File saved to: {OUT_PATH}")
    print("-" * 30)

if __name__ == "__main__":
    main()