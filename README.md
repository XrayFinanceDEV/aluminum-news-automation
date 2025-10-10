# Aluminum News Automation

Automazione RSS per notizie dell'industria dell'alluminio tramite GitHub Actions e Perplexity API.

## 📌 Cos'è

Questo progetto automatizza la raccolta di notizie sull'industria dell'alluminio utilizzando l'API di Perplexity. Lo script Python viene eseguito quotidianamente tramite GitHub Actions, genera un feed RSS e mantiene un database CSV delle notizie raccolte.

**Caratteristiche principali:**
- ✅ Raccolta automatica giornaliera di notizie
- ✅ Generazione feed RSS 2.0
- ✅ Database CSV con deduplicazione
- ✅ Classificazione automatica per categorie
- ✅ Zero costi di hosting (GitHub Actions + Pages)

## 🔧 Come Funziona

### Workflow

1. **Trigger Schedulato**: GitHub Actions esegue lo script quotidianamente
2. **Query Multiple**: Lo script interroga Perplexity API con query specifiche sull'alluminio
3. **Filtraggio e Classificazione**: Filtra notizie per data (ultime 24h) e classifica per categoria
4. **Database Management**: Salva i risultati in CSV con deduplicazione (mantiene ultimi 500 record)
5. **Generazione RSS**: Crea feed RSS 2.0 valido con metadata completi
6. **Pubblicazione**: Commit automatico su GitHub e pubblicazione tramite GitHub Pages

### Feed RSS

Il feed RSS generato è accessibile pubblicamente tramite GitHub Pages:
```
https://<USERNAME>.github.io/aluminum-news-automation/data/aluminum_news_feed.xml
```

## ⏰ Come Schedularlo

Lo scheduling è configurato nel file `.github/workflows/daily-news-update.yml`:

```yaml
on:
  schedule:
    - cron: '0 8 * * *'  # Esegue ogni giorno alle 08:00 UTC (10:00 CEST)
  workflow_dispatch:      # Permette esecuzione manuale
```

### Modificare la Frequenza di Esecuzione

Per cambiare l'orario o la frequenza, modifica la sintassi cron:

```yaml
# Esempi:
- cron: '0 */6 * * *'   # Ogni 6 ore
- cron: '0 12 * * *'    # Ogni giorno alle 12:00 UTC
- cron: '0 8 * * 1-5'   # Ogni giorno lavorativo alle 08:00 UTC
```

**Nota**: Usa [crontab.guru](https://crontab.guru/) per generare facilmente espressioni cron.

### Esecuzione Manuale

1. Vai su `Actions` nel repository
2. Seleziona workflow `Daily Aluminum News Update`
3. Click su `Run workflow` → `Run workflow`

## 🔍 Come Aggiornare le Query di Ricerca

Le query sono definite nel file `aluminum_news_automation.py` nella lista `queries`:

```python
queries = [
    "aluminum production news latest",
    "aluminum price trends market",
    "aluminum industry innovations",
    "aluminum recycling sustainability",
    "aluminum trade tariffs policy"
]
```

### Per Modificare le Query:

1. Apri `aluminum_news_automation.py`
2. Localizza la lista `queries` (solitamente all'inizio del main)
3. Aggiungi, rimuovi o modifica le stringhe di ricerca:

```python
queries = [
    "alluminio produzione Italia",                    # Aggiunta query italiana
    "aluminum LME price",                             # Focus su prezzi LME
    "aluminum electric vehicles battery",            # Settore automotive
    "aluminum packaging industry news",              # Settore packaging
    "bauxite mining aluminum production"             # Focus upstream
]
```

4. Commit e push delle modifiche
5. Le nuove query saranno utilizzate dalla prossima esecuzione schedulata

### Best Practices per le Query

- ✅ Usa termini specifici e settoriali
- ✅ Combina keyword generali + nicchia (es. "aluminum + automotive")
- ✅ Includi sinonimi e varianti (aluminum/aluminium)
- ✅ Evita query troppo generiche (restituiscono troppo rumore)
- ✅ Testa le query manualmente su Perplexity prima di aggiungerle

## 🔑 Requisiti Chiave e Setup API

### Prerequisiti

- Account GitHub (repository pubblico per GitHub Actions gratuito)
- API Key di Perplexity ([ottienila qui](https://www.perplexity.ai/api-platform))
- Python 3.10+ (per test locali)

### Configurazione API Secret

**⚠️ IMPORTANTE**: Non committare mai la API key nel codice!

1. Vai su `Settings` del repository GitHub
2. Click su `Secrets and variables` → `Actions`
3. Click su `New repository secret`
4. Configura:
   - **Name**: `PERPLEXITY_API_KEY` (deve essere esattamente questo nome)
   - **Value**: La tua API key (formato: `pplx-xxxxxxxxxx`)
5. Click `Add secret`

### Permessi GitHub Actions

1. Vai su `Settings` → `Actions` → `General`
2. Scroll a `Workflow permissions`
3. Seleziona `Read and write permissions`
4. Abilita `Allow GitHub Actions to create and approve pull requests`
5. Click `Save`

### Dipendenze Python

Il file `requirements.txt` contiene:

```
requests>=2.31.0
pandas>=2.0.0
feedgen>=1.0.0
python-dotenv>=1.0.0
pytz>=2024.1
beautifulsoup4>=4.12.0
```

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone https://github.com/<USERNAME>/aluminum-news-automation.git
cd aluminum-news-automation

# 2. Installa dipendenze (per test locali)
pip install -r requirements.txt

# 3. Crea file .env per test locali (NON committare!)
echo "PERPLEXITY_API_KEY=pplx-xxx" > .env

# 4. Test locale
python aluminum_news_automation.py

# 5. Verifica output
ls -la data/
cat data/aluminum_news_database.csv
cat data/aluminum_news_feed.xml
```

## 📊 Struttura File

```
aluminum-news-automation/
├── .github/
│   └── workflows/
│       └── daily-news-update.yml    # Configurazione GitHub Actions
├── data/
│   ├── aluminum_news_database.csv   # Database notizie (auto-generato)
│   └── aluminum_news_feed.xml       # Feed RSS (auto-generato)
├── aluminum_news_automation.py      # Script principale
├── requirements.txt                 # Dipendenze Python
├── .gitignore                       # File da ignorare (include .env)
└── README.md                        # Questa documentazione
```

## 🔧 Troubleshooting

### Il workflow non parte automaticamente
- Verifica che il workflow sia abilitato in `Actions`
- Controlla la sintassi cron in `daily-news-update.yml`
- I repository nuovi potrebbero richiedere una prima esecuzione manuale

### Errore "API Key not found"
- Verifica che il secret sia chiamato esattamente `PERPLEXITY_API_KEY`
- Ricontrolla di aver salvato correttamente il secret in Settings

### Errore "Permission denied" durante push automatico
- Vai in `Settings` → `Actions` → `Workflow permissions`
- Seleziona `Read and write permissions`

### RSS feed non valido
- Valida il feed con [W3C Feed Validator](https://validator.w3.org/feed/)
- Verifica che lo script generi XML ben formato
- Controlla i log in `Actions` per errori durante la generazione

## 📈 Monitoring

### Notifiche Email

Configura notifiche email per fallimenti:
1. `Settings` → `Notifications`
2. Abilita email per `Actions failures`

### Verifica Esecuzioni

- Vai su `Actions` per vedere storico esecuzioni
- Click su un workflow per vedere log dettagliati
- Verifica commit automatici per confermare aggiornamenti

## 📝 Limiti GitHub Actions

- Account gratuito: **2.000 minuti/mese**
- Questo workflow usa circa **2 minuti/giorno** = ~60 min/mese
- Ampio margine per account gratuito

## 📄 Licenza

MIT License - vedi repository per dettagli.

## 🤝 Contributi

Contributi, issue e feature request sono benvenuti!

---

**Generato con ❤️ per l'industria dell'alluminio**
