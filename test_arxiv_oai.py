import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def test_arxiv_oai():
    print("==================================================")
    # Reconfigure encoding for Windows CMD/PowerShell emoji printing
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        
    print("🛰️ Testing arXiv OAI-PMH Bulk Harvesting Protocol")
    print("==================================================\n")

    base_url = "https://export.arxiv.org/oai2"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Step 1: Identify the Repository
    print("[⏳] Step 1: Identifying repository connectivity...")
    try:
        resp = requests.get(base_url, params={"verb": "Identify"}, headers=headers, timeout=10)
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            print("    [✓] Repository successfully connected!")
            root = ET.fromstring(resp.text)
            # Find repositoryName
            repo_name = root.find(".//{http://www.openarchives.org/OAI/2.0/}repositoryName")
            if repo_name is not None:
                print(f"    Repository Name: {repo_name.text}")
        else:
            print(f"    [!] Failed to connect to OAI endpoint (Status: {resp.status_code})")
            return
    except Exception as e:
        print(f"    [!] Connection error: {e}")
        return

    # Step 2: List Recent Records from computer science (set=cs)
    print("\n[⏳] Step 2: Harvesting recent Computer Science records...")
    
    # Let's request records from 5 days ago to today
    from_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    params = {
        "verb": "ListRecords",
        "metadataPrefix": "arXiv",
        "set": "cs",
        "from": from_date
    }
    
    try:
        print(f"    Querying: {base_url} with set=cs, from={from_date}...")
        resp = requests.get(base_url, params=params, headers=headers, timeout=15)
        print(f"    Status: {resp.status_code} | Length: {len(resp.text)} bytes")
        
        if resp.status_code == 200:
            ns = {
                "oai": "http://www.openarchives.org/OAI/2.0/",
                "arxiv": "http://arxiv.org/OAI/arXiv/"
            }
            
            root = ET.fromstring(resp.text)
            records = root.findall(".//oai:record", ns)
            print(f"    [✓] Harvested {len(records)} recent records successfully!")
            
            # Parse and display the top 3 papers
            print("\n📰 Top 3 Harvested Papers:")
            print("-" * 50)
            
            count = 0
            for record in records:
                if count >= 3:
                    break
                    
                metadata = record.find(".//arxiv:arXiv", ns)
                if metadata is not None:
                    title = metadata.find("arxiv:title", ns)
                    authors = metadata.find("arxiv:authors", ns)
                    arxiv_id = metadata.find("arxiv:id", ns)
                    abstract = metadata.find("arxiv:abstract", ns)
                    
                    p_title = title.text.strip().replace("\n", " ") if title is not None else "Unknown Title"
                    p_id = arxiv_id.text.strip() if arxiv_id is not None else "Unknown ID"
                    
                    # Parse authors
                    author_list = []
                    if authors is not None:
                        for author in authors.findall("arxiv:author", ns):
                            keyname = author.find("arxiv:keyname", ns)
                            forenames = author.find("arxiv:forenames", ns)
                            fn = forenames.text.strip() if forenames is not None else ""
                            kn = keyname.text.strip() if keyname is not None else ""
                            author_list.append(f"{fn} {kn}".strip())
                    
                    print(f"ID: arXiv:{p_id}")
                    print(f"Title: {p_title}")
                    print(f"Authors: {', '.join(author_list[:3])}")
                    if abstract is not None:
                        print(f"Abstract: {abstract.text.strip()[:150]}...")
                    print("-" * 50)
                    count += 1
                    
        elif resp.status_code == 429:
            print("    [!] OAI-PMH rate limit (429) was triggered.")
        else:
            print(f"    [!] Error response from OAI-PMH server (Status: {resp.status_code})")
            
    except Exception as e:
        print(f"    [!] Exception occurred: {e}")

if __name__ == "__main__":
    test_arxiv_oai()
