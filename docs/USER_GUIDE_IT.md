# Guida Utente TimeClock

> Guida completa per utenti finali e amministratori

**Traduzioni:** [English](USER_GUIDE.md) | [Deutsch (German)](USER_GUIDE_DE.md)

---

## Indice

1. [Iniziare](#iniziare)
2. [Per i Dipendenti](#per-i-dipendenti)
3. [Per gli Amministratori](#per-gli-amministratori)
4. [Risoluzione Problemi](#risoluzione-problemi)

---

## Iniziare

### Primo Avvio

Quando avvii TimeClock per la prima volta, ti verrà chiesto di registrare un **Amministratore**. Questo passaggio è obbligatorio e non può essere saltato.

**Passaggi:**
1. Inserisci il nome completo dell'amministratore
2. Scansiona un badge RFID (o inserisci manualmente l'ID del tag)
3. La casella amministratore verrà automaticamente selezionata e bloccata
4. Clicca **Salva** per completare la registrazione

Una volta registrato, il badge dell'amministratore può essere utilizzato per accedere a tutte le funzioni di gestione.

---

## Per i Dipendenti

### Timbratura Ingresso/Uscita

**Come timbrare l'ingresso o l'uscita:**
1. Mettiti davanti al terminale TimeClock
2. Avvicina il tuo badge RFID al lettore
3. Attendi il lampeggio LED verde (conferma scansione riuscita)
4. Apparirà un messaggio di benvenuto (scompare dopo 8 secondi)
5. Il tuo stato verrà aggiornato sullo schermo

**Cosa succede:**
- Il sistema determina automaticamente se stai timbrando l'**INGRESSO** o l'**USCITA** in base alla tua ultima azione
- Se la tua ultima azione era USCITA (o non hai timbrato l'ingresso oggi), timbrerai l'**INGRESSO**
- Se la tua ultima azione era INGRESSO, timbrerai l'**USCITA**

### Visualizzazione Riepilogo Giornaliero

Dopo ogni azione di timbratura, vedrai:
- Un messaggio di benvenuto amichevole
- Un messaggio di stato che mostra la tua azione di timbratura (es. "Timbrato IN - Il Tuo Nome")
- Due pulsanti di azione:
  - **Visualizza Sessioni Oggi** - Vedi il dettaglio delle sessioni di oggi
  - **Modifica Sessioni Oggi** - Rimuovi scansioni duplicate o correggi errori

**Nota:** I pulsanti di azione rimangono sempre visibili. Se li clicchi dopo il periodo di grazia iniziale (2 minuti), dovrai scansionare nuovamente il badge per l'identificazione.

### Modifica delle Tue Timbrature

Puoi modificare le tue timbrature degli ultimi 7 giorni:

1. **Entro 2 minuti dalla timbratura:** Clicca **Modifica Sessioni Oggi** (nessuna scansione badge necessaria)
2. **Dopo 2 minuti:** Clicca **Modifica Sessioni Oggi** e scansiona il badge quando richiesto
3. Seleziona la data che vuoi modificare (solo ultimi 7 giorni)
4. Visualizza tutte le timbrature di quel giorno
5. Seleziona le timbrature da eliminare (rimuove scansioni duplicate)
6. Oppure aggiungi timbrature manuali se hai dimenticato di timbrare l'ingresso/uscita

**Importante:** Le timbrature eliminate non vengono rimosse permanentemente—sono contrassegnate come inattive per scopi di audit.

### Inserimento Manuale

Se hai dimenticato di timbrare l'ingresso o l'uscita:

1. Accedi all'editor delle timbrature (vedi sopra)
2. Clicca **Aggiungi Timbratura**
3. Seleziona la data (solo ultimi 7 giorni)
4. Imposta l'ora
5. Salva

**Nota:** Il sistema determina automaticamente se la timbratura deve essere INGRESSO o USCITA in base alle tue timbrature esistenti per quel giorno.

### Rimozione Scansioni Duplicate

**Problema:** Hai scansionato accidentalmente il badge due volte, creando timbrature duplicate.

**Soluzione:**
1. Clicca **Modifica Sessioni Oggi** (entro 2 minuti dalla timbratura, nessuna scansione badge necessaria)
2. Oppure scansiona badge → **Modifica Sessioni Oggi** (se sono passati più di 2 minuti)
3. Seleziona la data
4. Seleziona le timbrature duplicate
5. Clicca **Elimina Selezionate**
6. Conferma l'eliminazione

### Correzione Uscita Dimenticata

**Problema:** Hai dimenticato di timbrare l'uscita ieri.

**Soluzione:**
1. Scansiona badge → **Modifica Sessioni Oggi**
2. Seleziona la data di ieri
3. Clicca **Aggiungi Timbratura**
4. Imposta l'ora (es. fine giornata lavorativa)
5. Salva

Il sistema abbinerà automaticamente questa timbratura con l'ingresso esistente.

### Suggerimenti per i Dipendenti

- **Scansiona una volta:** Il sistema evita le scansioni rapide, ma è meglio scansionare una volta e attendere la conferma
- **Controlla il tuo stato:** Dopo la scansione, verifica che il messaggio di benvenuto mostri l'azione corretta (INGRESSO/USCITA)
- **Usa i pulsanti di azione:** Se noti un errore dopo la timbratura, usa i pulsanti di azione per modificare rapidamente le tue sessioni
- **Controlli regolari:** Rivedi periodicamente le tue timbrature per individuare eventuali problemi in anticipo

---

## Per gli Amministratori

### Accesso al Pannello Amministratore

Scansiona il tuo badge amministratore in qualsiasi momento per accedere al pannello amministratore. Lo schermo passerà automaticamente alla modalità amministratore.

### Registrazione Nuovi Dipendenti

1. Vai su **Admin → Registra Utente**
2. Inserisci il nome completo del dipendente
3. Scansiona il loro badge RFID (o inserisci manualmente l'ID del tag)
4. Lascia la casella amministratore **deselezionata** (a meno che non stai creando un altro amministratore)
5. Clicca **Salva**

**Nota:** Ogni badge può essere assegnato a un solo dipendente. Se provi a registrare un badge già in uso, vedrai un messaggio di errore.

### Identificazione Badge

Per verificare a quale dipendente appartiene un badge:

1. Vai su **Admin → Identifica Tag**
2. Scansiona il badge
3. Visualizza le informazioni mostrate:
   - Nome del dipendente
   - ID Tag
   - Ruolo (Amministratore o Dipendente)
   - Stato di registrazione

### Generazione Report Orario di Lavoro

1. Vai su **Admin → Report WT**
2. Seleziona un dipendente dal menu a tendina
3. (Opzionale) Imposta un intervallo di date:
   - Clicca **Seleziona Date**
   - Scegli le date di inizio e fine
   - Clicca **Conferma**
4. Clicca **Genera Report**
5. Rivedi il report che mostra:
   - Dettaglio giornaliero delle sessioni
   - Orari di ingresso/uscita
   - Durata per sessione
   - Totali giornalieri
   - Riepilogo periodo (ore totali, media giornaliera)
6. Opzioni di esportazione:
   - **Esporta in Excel** - Foglio di calcolo strutturato con ore per giorno per mese
   - **Esporta in CSV** - Formato delimitato da punto e virgola per sistemi di busta paga
   - **Esporta in PDF** - Report formattato per la stampa

**Caratteristiche del Report:**
- Abbina automaticamente gli eventi di ingresso e uscita
- Calcola le ore totali lavorate dalle timbrature effettive
- Mostra le medie giornaliere
- Segnala sessioni aperte (se il dipendente ha dimenticato di timbrare l'uscita)
- I formati di esportazione mostrano le ore per giorno organizzate per mese

**Formato di Esportazione:**
I file esportati mostrano le ore di lavoro per giorno in un formato semplice e chiaro:
- Nome del dipendente e intervallo di date in alto
- Ogni mese elencato separatamente
- Numeri dei giorni (1-31) in alto
- Ore lavorate per giorno nel formato H:MM sotto
- Totali mensili nella colonna più a destra

### Esportazione Dati

**Esporta Timbrature Grezze (CSV):**
1. Vai su **Admin → Esporta CSV**
2. Clicca **Esporta Timbrature**
3. Il file verrà salvato su unità USB (se collegata) o nella directory `exports/`
4. Un popup di conferma mostra il percorso del file
5. Contiene le timbrature grezze di ingresso/uscita con timestamp

**Esporta Report Ore di Lavoro:**
1. Vai su **Admin → Report WT**
2. Seleziona dipendente e intervallo di date
3. Genera report
4. Scegli formato di esportazione:
   - **Excel** - Per applicazioni di fogli di calcolo (`.xlsx`)
   - **CSV** - Per import in sistemi di busta paga (`.csv`, delimitato da punto e virgola)
   - **PDF** - Per stampa e documentazione (`.pdf`)
5. I file vengono salvati nel formato: `Arbeitszeit_[NomeDipendente]_[DataInizio]_[DataFine].[ext]`

**Esporta Backup Database:**
1. Vai su **Admin → Esporta Database**
2. Clicca **Esporta Database**
3. Verrà creato un backup completo del database SQLite
4. Utile per backup o migrazione a un altro sistema

**Posizioni di Esportazione:**
- Le unità USB vengono rilevate automaticamente (`/media`, `/run/media`, `/mnt`)
- Se non viene trovata una USB, i file vengono salvati nella directory `exports/`
- Puoi sovrascrivere con la variabile d'ambiente: `export TIME_CLOCK_EXPORT_PATH=/percorso/personalizzato`

### Suggerimenti per gli Amministratori

- **Backup regolari:** Esporta il database regolarmente per scopi di backup
- **Monitoraggio report:** Genera report settimanali per individuare pattern o problemi
- **Gestione badge:** Tieni traccia di quali badge sono assegnati a quali dipendenti
- **Test hardware:** Testa periodicamente la funzionalità del lettore RFID utilizzando la funzione Identifica Tag

---

## Risoluzione Problemi

### Badge Non Riconosciuto

**Sintomi:** Lampeggio LED rosso, messaggio "Tag Sconosciuto"

**Soluzioni:**
- Assicurati che il badge sia tenuto vicino al lettore (entro 2-3 cm)
- Prova a scansionare di nuovo (attendi 1-2 secondi tra le scansioni)
- Verifica se il badge è registrato: Admin → Identifica Tag
- Contatta l'amministratore per registrare il badge

### Impossibile Accedere alle Funzioni Admin

**Sintomi:** Il badge amministratore non passa alla schermata admin

**Soluzioni:**
- Verifica che il badge sia registrato come amministratore
- Controlla l'assegnazione del badge: Admin → Identifica Tag
- Assicurati di scansionare il badge corretto
- Prova a riavviare l'applicazione

### Esportazione Non Funziona

**Sintomi:** Il pulsante di esportazione non crea il file, o il file non viene trovato

**Soluzioni:**
- Verifica che l'unità USB sia montata correttamente
- Verifica che la USB abbia i permessi di scrittura
- Controlla che la directory `exports/` esista e sia scrivibile
- Rivedi i log dell'applicazione per messaggi di errore
- Prova a impostare un percorso di esportazione personalizzato: `export TIME_CLOCK_EXPORT_PATH=/tmp`

### Schermo Diventa Vuoto (Screensaver)

**Sintomi:** Lo schermo mostra un'animazione stile Matrix dopo inattività

**Soluzioni:**
- Questo è un comportamento normale (si attiva dopo 60 secondi di inattività)
- Tocca lo schermo o scansiona un badge per svegliarlo
- Lo schermo tornerà alla schermata precedente

### Pulsanti Non Rispondono

**Sintomi:** Il pulsante appare premuto ma non attiva l'azione

**Soluzioni:**
- Assicurati di completare il tocco (premi e rilascia)
- Attendi un momento tra i tocchi (i doppi tocchi rapidi vengono ignorati)
- Con touchscreen: assicurati che il dito si sollevi completamente prima di toccare di nuovo

---

*Ultimo aggiornamento: Gen 2026*
