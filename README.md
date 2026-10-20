# Σήματα, ROUTER–DEALER και dictionaries

## 1. Σκοπός

Επικοινωνία ενός ROUTER με τρεις DEALER (`P1`, `P2`, `P3`), αποθήκευση
πληροφοριών ανά συναλλαγή και ενεργοποίηση των απαντήσεων με SIGINT (Ctrl+C).
Χρησιμοποιούνται τα αρχεία `router.py` και `dealer.py`.

## 2. Εγκατάσταση και εκτέλεση

Απαιτούνται Python 3 και pyzmq:

```text
python -m pip install pyzmq
```

Στο `router.py` ορίστε:

```python
NUM_DEALERS = 3
NUM_MESSAGES = 3
```

Ανοίξτε τέσσερις κονσόλες στον φάκελο των αρχείων και εκτελέστε με τη σειρά,
μία εντολή σε κάθε κονσόλα:

```text
python router.py
python dealer.py P1
python dealer.py P2
python dealer.py P3
```

Αν χρησιμοποιείτε τον εκκινητή `py`, αντικαταστήστε το `python` με `py`.
Το ROUTER κάνει bind στη θύρα 5555 και οι DEALER συνδέονται στο
`tcp://localhost:5555`.

## 3. Ροή της επίδειξης

1. Κάθε DEALER στέλνει `HELLO` με το όνομά του. Το ROUTER αποθηκεύει
   τις τρεις ταυτότητες δρομολόγησης.
2. Μετά τα τρία HELLO, το ROUTER στέλνει σε κάθε DEALER τρία μηνύματα:

   ```text
   PREPARE T1 C1 100
   PREPARE T2 C2 200
   PREPARE T3 C3 300
   ```

3. Οι DEALER αποθηκεύουν τα μηνύματα χωρίς να απαντούν αμέσως.
4. Αφού εμφανιστούν και τα τρία μηνύματα σε κάθε DEALER, πατήστε Ctrl+C
   πρώτα στον P2 και έπειτα στους P1 και P3.
5. Κάθε DEALER απαντά για τις συναλλαγές με σειρά `T3`, `T2`, `T1` και
   τερματίζει. Το ROUTER τερματίζει μετά από εννέα συνολικά απαντήσεις.

Κάθε DEALER έχει δικό του dictionary για τη φύλαξη και διαχείρηση των μηνυμάτων. Τα ίδια τρία transactionId αποστέλλονται και στους τρεις DEALER. Αν πατηθεί πρόωρα Ctrl+C, κάποια μηνύματα μπορεί να μην έχουν αποθηκευτεί· για νέα επίδειξη επανεκκινήστε και τις τέσσερις διεργασίες.

## 4. ROUTER–DEALER και frames

Δεν απαιτείται αυστηρή εναλλαγή αποστολής–παραλαβής, το μοτίβο είναι ασύγχρονο: το ROUTER στέλνει όλα τα αιτήματα πριν συλλέξει τις απαντήσεις.

Στη λήψη από το ROUTER:

```python
identity, payload = router.recv_multipart()
```

- `identity`: frame ταυτότητας του αποστολέα, π.χ. `b"P1"`.
- `payload`: frame περιεχομένου, π.χ. `b"HELLO P1"`.

Για αποστολή σε συγκεκριμένο DEALER:

```python
router.send_multipart([identity, message.encode()])
```

Το πρώτο frame επιλέγει τον παραλήπτη και αφαιρείται κατά τη δρομολόγηση.
Ο DEALER παραλαμβάνει μόνο το περιεχόμενο (payload) με `recv_string()` και απαντά
με `send_string()`. Δεν προσθέτουμε κενό frame. Η identity διατηρείται
ως bytes· τα `encode()` και `decode()` μετατρέπουν μεταξύ string και bytes.

## 5. Μήνυμα και dictionary ανά συναλλαγή

Το ROUTER κατασκευάζει το string με f-string:

```python
message = f"PREPARE {transaction_id} {client_id} {amount}"
```

Ο DEALER χωρίζει τα τέσσερα πεδία και αποθηκεύει μία εγγραφή ανά transactionId:

```python
msg_type, transaction_id, client_id, amount = message.split()

pending[transaction_id] = {
    "type": msg_type,
    "client_id": client_id,
    "amount": int(amount)
}
```

Για την T1 η εγγραφή είναι:

```python
pending["T1"] = {
    "type": "PREPARE",
    "client_id": "C1",
    "amount": 100
}
```
Μετά την παραλαβή των τριών μηνυμάτων:

```python
pending = {
    "T1": {"type": "PREPARE", "client_id": "C1", "amount": 100},
    "T2": {"type": "PREPARE", "client_id": "C2", "amount": 200},
    "T3": {"type": "PREPARE", "client_id": "C3", "amount": 300}
}
```

Παραδείγματα πρόσβασης:

```python
pending["T1"]               # Ολόκληρη η εγγραφή της T1.
pending["T1"]["client_id"]  # "C1"
pending["T1"]["amount"]     # 100
```

Ή μέσα στον βρόχο απαντήσεων:

```python
transaction = pending[transaction_id]
print(transaction["client_id"], transaction["amount"])
```

Αν χρησιμοποιηθεί ξανά το ίδιο κλειδί, η ανάθεση αντικαθιστά την προηγούμενη
εγγραφή. Στην επίδειξη κάθε DEALER λαμβάνει μία φορά κάθε transactionId.

## 6. SIGINT και αναμονή μηνυμάτων
Η εντολή:

```python
signal.signal(signal.SIGINT, on_ctrl_c)
```

δηλώνει τον διαχειριστή (handler) ενός σήματος, δηλαδή ποια συνάρτηση θα εκτελεί η Python όταν η διεργασία λάβει κάποιο σήμα, στη δική μας περίπτωση το SIGINT.

Ο handler θέτει:

```python
global reply_now
reply_now = True
```

Το global χρειάζεται επειδή η ανάθεση πρέπει να αλλάξει τη μεταβλητή
του κύριου προγράμματος, όχι να δημιουργήσει τοπική μεταβλητή.
Η αποστολή των απαντήσεων γίνεται μετά τον βρόχο, όχι μέσα στον handler.

Οι παράμετροι του handler είναι:

- signum: αριθμός σήματος, εδώ SIGINT.
- frame: πλαίσιο εκτέλεσης της Python, όχι frame μηνύματος ZeroMQ.


```python
while not reply_now:
    if dealer.poll(500):
        message = dealer.recv_string()
```

Η `poll(500)` περιμένει έως 500 ms για μήνυμα. Το timeout επιτρέπει
τακτική επιστροφή στην Python για εξυπηρέτηση του σήματος και έλεγχο
της σημαίας, ακόμη και χωρίς νέο μήνυμα. 

## 7. Απαντήσεις με αντίστροφη σειρά

```python
for transaction_id in reversed(list(pending)):
    dealer.send_string(f"PREPARED {transaction_id}")
```

Τα κλειδιά ανακτώνται με τη σειρά εισαγωγής και αντιστρέφονται εσκεμμένα.
Η αλλαγή σειράς γίνεται από την εφαρμογή, όχι από το ZeroMQ.
Η `identity` δείχνει ποιος απάντησε και το `transactionId` σε ποιο αίτημα. 
Ο παραλήπτης αναγνωρίζει τη συναλλαγή από το transactionId, όχι από
τη θέση της απάντησης σε μια σειρά.

## 8. Αυτόματη ταυτότητα δρομολόγησης

Για επίδειξη αυτόματης ταυτότητας, σχολιάστε στον DEALER:

```python
# dealer.identity = name.encode()
```

Το ZeroMQ αναθέτει ταυτότητα χωρίς να την ορίσει η εφαρμογή. Στο ROUTER
αντικαταστήστε όλες τις εκτυπώσεις `identity.decode()` με `identity!r`, π.χ.:

```python
print(f"Identity: {identity!r}, payload: {payload.decode()}")
```

Η αυτόματη ταυτότητα είναι δυαδική και δεν θεωρείται κείμενο UTF-8.
Η αποστολή εξακολουθεί να χρησιμοποιεί την αρχική τιμή `identity`.
Επανεκκινήστε και τις τέσσερις διεργασίες για να συγκρίνετε τις ταυτότητες και
επιβεβαιώστε ότι τα μηνύματα παραδίδονται κανονικά.
