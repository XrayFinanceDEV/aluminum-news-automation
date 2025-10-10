# 5. Client Notion (src/notion_client.py)
notion_client_code = '''import os
from notion_client import Client
from datetime import datetime
import re

class NotionClient:
    def __init__(self, token, database_id):
        self.client = Client(auth=token)
        self.database_id = database_id
    
    def parse_markdown_table(self, markdown_content):
        """Estrae dati dalla tabella markdown generata da Perplexity"""
        lines = markdown_content.split('\\n')
        
        # Trova la tabella markdown
        table_start = -1
        for i, line in enumerate(lines):
            if '|' in line and ('Data' in line or 'Argomento' in line):
                table_start = i
                break
        
        if table_start == -1:
            print("Tabella markdown non trovata")
            return []
        
        # Estrae header e dati
        header_line = lines[table_start]
        separator_line = lines[table_start + 1] if table_start + 1 < len(lines) else ""
        
        # Salta header e separator
        data_lines = []
        for i in range(table_start + 2, len(lines)):
            line = lines[i].strip()
            if line and '|' in line:
                data_lines.append(line)
            elif line == "":
                continue
            else:
                break  # Fine tabella
        
        # Parse dei dati
        parsed_data = []
        for line in data_lines:
            # Rimuovi | iniziali e finali e splitta
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            
            if len(cells) >= 5:
                data_entry = {
                    "data": cells[0],
                    "categoria": cells[1], 
                    "titolo": cells[2],
                    "estratto": cells[3],
                    "fonte": cells[4]
                }
                parsed_data.append(data_entry)
        
        return parsed_data
    
    def save_to_database(self, research_data, perplexity_response):
        """Salva i dati nel database Notion"""
        
        # Parse della tabella markdown
        parsed_entries = self.parse_markdown_table(perplexity_response["content"])
        
        results = []
        
        for entry in parsed_entries:
            try:
                # Crea la pagina in Notion
                new_page = self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties={
                        "Titolo": {
                            "title": [
                                {
                                    "text": {
                                        "content": entry["titolo"][:100]  # Limite lunghezza
                                    }
                                }
                            ]
                        },
                        "Data": {
                            "date": {
                                "start": datetime.now().strftime("%Y-%m-%d")
                            }
                        },
                        "Categoria": {
                            "select": {
                                "name": entry["categoria"][:100]
                            }
                        },
                        "Estratto": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": entry["estratto"][:2000]
                                    }
                                }
                            ]
                        },
                        "Fonte": {
                            "url": entry["fonte"] if entry["fonte"].startswith("http") else None
                        },
                        "Timestamp_Ricerca": {
                            "date": {
                                "start": datetime.fromisoformat(perplexity_response["timestamp"].replace('Z', '+00:00')).strftime("%Y-%m-%d")
                            }
                        },
                        "Token_Usage": {
                            "number": perplexity_response.get("usage", {}).get("total_tokens", 0)
                        }
                    }
                )
                
                results.append({
                    "status": "success",
                    "page_id": new_page["id"],
                    "title": entry["titolo"][:50]
                })
                
            except Exception as e:
                print(f"Errore salvando entry: {e}")
                results.append({
                    "status": "error", 
                    "error": str(e),
                    "title": entry.get("titolo", "Unknown")[:50]
                })
        
        return results
    
    def create_database_if_not_exists(self):
        """Crea il database Notion se non esiste (richiede page parent)"""
        # Nota: Questo richiede che il database sia già creato manualmente
        # o che si abbia accesso a una pagina parent
        pass
'''

print("=== NOTION CLIENT (src/notion_client.py) ===")
print(notion_client_code)