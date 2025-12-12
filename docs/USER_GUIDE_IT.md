# Guida Utente TimeClock

> Guida completa per utenti finali e amministratori

---

## Indice

1. [Iniziare](#iniziare)
2. [Per i Dipendenti](#per-i-dipendenti)
3. [Per gli Amministratori](#per-gli-amministratori)
4. [Attività Comuni](#attività-comuni)
5. [Risoluzione Problemi](#risoluzione-problemi)

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
4. Apparirà un messaggio di benvenuto
5. Il tuo stato verrà aggiornato sullo schermo

**Cosa succede:**
- Il sistema determina automaticamente se stai timbrando l'**INGRESSO** o l'**USCITA** in base alla tua ultima azione
- Se la tua ultima azione era USCITA (o non hai timbrato l'ingresso oggi), timbrerai l'**INGRESSO**
- Se la tua ultima azione era INGRESSO, timbrerai l'**USCITA**

### Visualizzazione Riepilogo Giornaliero

Dopo ogni azione di timbratura, vedrai:
- Un messaggio di benvenuto amichevole (scompare dopo 3 secondi)
- Un messaggio di stato che mostra la tua azione di timbratura (es. "Timbrato IN - Il Tuo Nome")
- Due pulsanti di azione sempre disponibili:
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
4. Scegli **Ingresso** o **Uscita**
5. Imposta l'ora
6. Salva

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
6. (Opzionale) Clicca **Esporta in CSV** per salvare per la busta paga

**Caratteristiche del Report:**
- Abbina automaticamente gli eventi di ingresso e uscita
- Calcola le ore totali lavorate
- Mostra le medie giornaliere
- Segnala sessioni aperte (se il dipendente ha dimenticato di timbrare l'uscita)

### Esportazione Dati

**Esporta Timbrature Grezze:**
1. Vai su **Admin → Esporta CSV**
2. Clicca **Esporta Timbrature**
3. Il file verrà salvato su unità USB (se collegata) o nella directory `exports/`
4. Un popup di conferma mostra il percorso del file

**Esporta Backup Database:**
1. Vai su **Admin → Esporta Database**
2. Clicca **Esporta Database**
3. Verrà creato un backup completo del database SQLite
4. Utile per backup o migrazione a un altro sistema

**Posizioni di Esportazione:**
- Le unità USB vengono rilevate automaticamente (`/media`, `/run/media`, `/mnt`)
- Se non viene trovata una USB, i file vengono salvati nella directory `exports/`
- Puoi sovrascrivere con la variabile d'ambiente: `export TIME_CLOCK_EXPORT_PATH=/percorso/personalizzato`

---

## Attività Comuni

### Rimozione Scansioni Duplicate

**Problema:** Il dipendente ha scansionato accidentalmente il badge due volte, creando timbrature duplicate.

**Soluzione:**
1. Clicca **Modifica Sessioni Oggi** (entro 2 minuti dalla timbratura, nessuna scansione badge necessaria)
2. Oppure scansiona badge → **Modifica Sessioni Oggi** (se sono passati più di 2 minuti)
3. Seleziona la data
4. Seleziona le timbrature duplicate
5. Clicca **Elimina Selezionate**
6. Conferma l'eliminazione

Le timbrature duplicate verranno rimosse dai report ma conservate nel database per scopi di audit.

### Correzione Uscita Dimenticata

**Problema:** Il dipendente ha dimenticato di timbrare l'uscita ieri.

**Soluzione:**
1. Scansiona badge → **Modifica Sessioni Oggi**
2. Seleziona la data di ieri
3. Clicca **Aggiungi Timbratura**
4. Scegli **Uscita**
5. Imposta l'ora (es. fine giornata lavorativa)
6. Salva

Il sistema abbinerà automaticamente questa timbratura con l'ingresso esistente.

### Visualizzazione Ore Dipendente

**Per i dipendenti:**
- Visualizza il riepilogo di oggi immediatamente dopo la timbratura
- Oppure scansiona badge → **Visualizza Report Oggi**

**Per gli amministratori:**
- Vai su **Admin → Report WT**
- Seleziona dipendente e intervallo di date
- Genera report

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

### Input Doppio Carattere

**Sintomi:** Quando si digita, ogni carattere appare due volte

**Soluzioni:**
- Questo viene gestito automaticamente dall'applicazione
- Se persiste, prova a toccare più lentamente
- Il sistema filtra automaticamente i tasti duplicati

---

## Suggerimenti e Best Practice

### Per i Dipendenti

- **Scansiona una volta:** Il sistema evita le scansioni rapide, ma è meglio scansionare una volta e attendere la conferma
- **Controlla il tuo stato:** Dopo la scansione, verifica che il messaggio di benvenuto mostri l'azione corretta (INGRESSO/USCITA)
- **Usa i pulsanti di azione:** Se noti un errore dopo la timbratura, usa i pulsanti di azione per modificare rapidamente le tue sessioni
- **Controlli regolari:** Rivedi periodicamente le tue timbrature per individuare eventuali problemi in anticipo

### Per gli Amministratori

- **Backup regolari:** Esporta il database regolarmente per scopi di backup
- **Monitoraggio report:** Genera report settimanali per individuare pattern o problemi
- **Gestione badge:** Tieni traccia di quali badge sono assegnati a quali dipendenti
- **Test hardware:** Testa periodicamente la funzionalità del lettore RFID utilizzando la funzione Identifica Tag

---

## Supporto

Per problemi tecnici o domande:
- Controlla la sezione di risoluzione problemi sopra
- Rivedi i log dell'applicazione
- Contatta il tuo amministratore di sistema

---

*Ultimo aggiornamento: Dic 2025*

