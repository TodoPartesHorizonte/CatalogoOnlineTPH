import json

transcript_path = r"C:\Users\Miguel F\.gemini\antigravity-ide\brain\3bf54561-1170-483c-9693-b605b7c3d61d\.system_generated\logs\transcript.jsonl"

with open(transcript_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'matches_vehicle_filter' in line or 'generate_vehicle_hub_pages' in line:
            try:
                obj = json.loads(line)
                content = obj.get('content', '')
                if 'def ' in content or 'replace_outer_div' in content:
                    print(f"Line {i} content contains python code:")
                    print(content[:1500])
                    print("="*50)
                
                # Check tool calls
                for tc in obj.get('tool_calls', []):
                    args = tc.get('args', {})
                    for k, v in args.items():
                        if isinstance(v, str) and ('def ' in v or 'replace_outer_div' in v):
                            print(f"Line {i} tool call arg {k} contains code:")
                            print(v[:1500])
                            print("="*50)
                            
                # Check output
                output = obj.get('output', '')
                if isinstance(output, str) and ('def ' in output or 'replace_outer_div' in output):
                    print(f"Line {i} output contains code:")
                    print(output[:1500])
                    print("="*50)
            except Exception as e:
                pass
