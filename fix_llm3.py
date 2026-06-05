import re

with open('app/core/llm/deepinfra_llm.py', 'r', encoding='utf-8') as f:
    code = f.read()

start_idx = code.find('                                chunk = data["choices"][0]["delta"].get("content", "")')
end_idx = code.find('                            except Exception as e:', start_idx)

if start_idx != -1 and end_idx != -1:
    new_code = '''                                chunk = data["choices"][0]["delta"].get("content", "")
                                if not chunk: continue
                                
                                if not hasattr(self, "_last_cum"):
                                    self._last_cum = ""
                                    self._think_state = 0
                                    self._think_buf = ""
                                    
                                # 1. Convert to true delta (works for both cumulative and delta inputs)
                                if chunk.startswith(self._last_cum):
                                    delta = chunk[len(self._last_cum):]
                                else:
                                    delta = chunk
                                self._last_cum = chunk
                                
                                if not delta: continue
                                
                                # 2. State machine to filter <think> tags from true deltas
                                clean_delta = ""
                                if self._think_state == 0:
                                    self._think_buf += delta
                                    b = self._think_buf.lstrip()
                                    
                                    if b.startswith("<think>"):
                                        self._think_state = 1
                                        self._think_buf = b[7:]
                                        if "</think>" in self._think_buf:
                                            self._think_state = 2
                                            clean_delta = self._think_buf.split("</think>", 1)[1].lstrip("\\n")
                                            self._think_buf = ""
                                    elif "<think>".startswith(b):
                                        pass # wait
                                    else:
                                        self._think_state = 2
                                        clean_delta = self._think_buf
                                        self._think_buf = ""
                                        
                                elif self._think_state == 1:
                                    self._think_buf += delta
                                    if "</think>" in self._think_buf:
                                        self._think_state = 2
                                        clean_delta = self._think_buf.split("</think>", 1)[1].lstrip("\\n")
                                        self._think_buf = ""
                                        
                                elif self._think_state == 2:
                                    clean_delta = delta
                                    
                                if clean_delta:
                                    yield clean_delta
'''
    code = code[:start_idx] + new_code + code[end_idx:]
    with open('app/core/llm/deepinfra_llm.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print("Replaced!")
else:
    print("Could not find boundaries!")
