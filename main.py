import os
import re
import math
import requests
import subprocess
from urllib.parse import urljoin, urlparse

def hms_to_seconds(hms: str) -> float:
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def is_absolute(u: str) -> bool:
    return urlparse(u).scheme in ("http", "https")

def make_absolute(base_url: str, u: str) -> str:
    return u if is_absolute(u) else urljoin(base_url, u)

def shorten_m3u8_by_time(m3u8_url: str, output_m3u8: str, start_hms: str, end_hms: str) -> dict:
    print(f"\nDownloading m3u8 from {m3u8_url} ...")
    r = requests.get(m3u8_url)
    r.raise_for_status()
    raw_lines = r.text.strip().splitlines()

    # Derive base URL from the m3u8 URL
    base_url = m3u8_url.rsplit("/", 1)[0] + "/"

    # Remove any TOTAL DURATION (underscore or hyphen; any casing)
    total_dur_re = re.compile(r"#EXT-X-TOTAL[-_]DURATION", re.IGNORECASE)
    lines = [ln.strip() for ln in raw_lines if not total_dur_re.match(ln.strip())]

    start_sec = hms_to_seconds(start_hms)
    end_sec = hms_to_seconds(end_hms)
    if end_sec <= start_sec:
        raise ValueError("end time must be greater than start time")

    # Collect header-ish info seen before first EXTINF
    saw_first_extinf = False
    version_line = None
    playlist_type_line = None
    independent_line = None
    original_targetduration = None
    media_sequence_original = None
    key_lines_abs = []      # keep keys (with absolute URI)
    map_line_abs = None     # keep the first EXT-X-MAP (absolute)

    # Pass 1: scan & capture headers + build segment list
    segments = []  # list of dicts: {dur, uri, raw_extinf, index_int or None}
    current_time = 0.0
    i = 0
    while i < len(lines):
        ln = lines[i]

        if not saw_first_extinf:
            if ln.startswith("#EXT-X-VERSION"):
                version_line = ln
            elif ln.startswith("#EXT-X-PLAYLIST-TYPE"):
                playlist_type_line = ln
            elif ln.startswith("#EXT-X-INDEPENDENT-SEGMENTS"):
                independent_line = ln
            elif ln.startswith("#EXT-X-TARGETDURATION"):
                try:
                    original_targetduration = int(ln.split(":",1)[1].strip())
                except Exception:
                    pass
            elif ln.startswith("#EXT-X-MEDIA-SEQUENCE"):
                try:
                    media_sequence_original = int(ln.split(":",1)[1].strip())
                except Exception:
                    pass
            elif ln.startswith("#EXT-X-KEY"):
                # Rewrite URI (if present) to absolute
                m = re.search(r'URI="([^"]+)"', ln)
                if m:
                    abs_key = make_absolute(base_url, m.group(1))
                    ln = re.sub(r'URI="[^"]+"', f'URI="{abs_key}"', ln)
                key_lines_abs.append(ln)
            elif ln.startswith("#EXT-X-MAP"):
                # Rewrite map to absolute
                m = re.search(r'URI="([^"]+)"', ln)
                if m:
                    abs_map = make_absolute(base_url, m.group(1))
                    ln = re.sub(r'URI="[^"]+"', f'URI="{abs_map}"', ln)
                # Keep the last seen map before first segment ( usually there’s only one )
                map_line_abs = ln

        if ln.startswith("#EXTINF"):
            saw_first_extinf = True
            # Duration
            try:
                dur = float(ln.split(":",1)[1].split(",")[0].strip())
            except Exception:
                dur = 0.0
            # Next non-empty line should be the segment URI
            if i + 1 >= len(lines):
                break
            uri_line = lines[i+1].strip()
            # store
            seg = {
                "dur": dur,
                "uri": uri_line,
                "raw_extinf": ln,
                "index": None
            }
            # Try to extract numeric index from filename (e.g., seg-123.m4s?cv=v1 -> 123)
            mnum = re.search(r'(\d+)(?=[^0-9]*$)', uri_line)
            if mnum:
                try:
                    seg["index"] = int(mnum.group(1))
                except Exception:
                    seg["index"] = None

            segments.append(seg)
            current_time += dur
            i += 2
            continue

        i += 1

    # Build time mapping to select by timestamp
    selected = []
    t_cursor = 0.0
    for seg in segments:
        seg_start = t_cursor
        seg_end = t_cursor + seg["dur"]
        # Select segment if it intersects [start_sec, end_sec]
        if seg_end > start_sec and seg_start < end_sec:
            selected.append(seg)
        # Early break if we passed end
        if seg_start >= end_sec:
            break
        t_cursor = seg_end

    if not selected:
        raise RuntimeError("No segments fall within the requested time range.")

    # Recompute headers for the shortened list
    # TargetDuration: integer ceil of the max segment duration in the selection
    max_dur = max((s["dur"] for s in selected), default=0.0)
    target_duration = int(math.ceil(max_dur)) if max_dur > 0 else (original_targetduration or 10)

    # MEDIA-SEQUENCE: use the index from first selected segment if available, else 0
    if selected[0]["index"] is not None:
        media_sequence = selected[0]["index"]
    else:
        # Fallback: keep original media sequence if present, otherwise 0
        media_sequence = media_sequence_original if media_sequence_original is not None else 0

    # Sum exact total duration of selected segments
    total_duration = sum(s["dur"] for s in selected)

    # Build the new playlist
    out = []
    out.append("#EXTM3U")
    out.append(f"#EXT-X-VERSION:{(version_line.split(':',1)[1].strip() if version_line else '6')}")
    if independent_line:
        out.append(independent_line)
    if playlist_type_line:
        out.append(playlist_type_line)
    out.append(f"#EXT-X-TARGETDURATION:{target_duration}")
    out.append(f"#EXT-X-MEDIA-SEQUENCE:{media_sequence}")
    if key_lines_abs:
        out.extend(key_lines_abs)
    if map_line_abs:
        out.append(map_line_abs)

    # Write selected segments with absolute URLs
    for s in selected:
        out.append(s["raw_extinf"])
        abs_uri = make_absolute(base_url, s["uri"])
        out.append(abs_uri)

    # Footer: ENDLIST then TOTAL_DURATION (underscore variant as you requested)
    out.append("#EXT-X-ENDLIST")
    out.append(f"#EXT-X-TOTAL_DURATION:{total_duration:.6f}")

    # Save the shortened playlist
    with open(output_m3u8, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print(f"\nShortened m3u8 saved to: {output_m3u8}")
    print(f"Base URL (auto): {base_url}")
    print(f"Selected duration: {total_duration:.3f}s  |  Segments: {len(selected)}  |  TARGETDURATION: {target_duration}")
    return {
        "output_m3u8": output_m3u8,
        "duration": total_duration,
        "segments": len(selected)
    }

def download_with_ffmpeg(local_m3u8: str, output_mp4: str):
    cmd = [
        "ffmpeg",
        "-y",
        "-protocol_whitelist", "file,http,https,tcp,tls",
        "-allowed_extensions", "ALL",
        "-i", local_m3u8,
        "-c", "copy",
        output_mp4
    ]
    print(f"\nDownloading to {output_mp4} ...\n")
    subprocess.run(cmd, check=True)
    print(f"Download completed: {output_mp4}")

if __name__ == "__main__":
    try:
        m3u8_url = input("Enter m3u8 URL: ").strip()
        start_hms = input("Start time (HH:MM:SS): ").strip()
        end_hms = input("End time   (HH:MM:SS): ").strip()
        out_m3u8 = input("Output m3u8 filename (default: clipped.m3u8): ").strip() or "clipped.m3u8"

        info = shorten_m3u8_by_time(m3u8_url, out_m3u8, start_hms, end_hms)

        choice = input("\nDownload now with ffmpeg? (y/N): ").strip().lower()
        if choice == "y":
            default_mp4 = os.path.splitext(os.path.basename(out_m3u8))[0] + ".mp4"
            out_mp4 = input(f"Output MP4 filename (default: {default_mp4}): ").strip() or default_mp4
            download_with_ffmpeg(out_m3u8, out_mp4)
        else:
            print("Skipping download.")
    except Exception as e:
        print(f"\nError: {e}")