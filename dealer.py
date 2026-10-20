import signal
import sys
import zmq

name = sys.argv[1]
# global flag: ο handler τη θέτει σε True και ο κύριος βρόχος την ελέγχει.
reply_now = False

def on_ctrl_c(signum, frame):
    # Χωρίς global, η ανάθεση θα δημιουργούσε τοπική μεταβλητή και δεν θα
    # άλλαζε τo flag που ελέγχει ο κύριος βρόχος.
    global reply_now
    reply_now = True

# Αντικαθιστούμε τη συνηθισμένη συμπεριφορά του Ctrl+C με τον δικό μας handler.
# Το Ctrl+C εδώ ενεργοποιεί τις απαντήσεις αντί να προκαλεί KeyboardInterrupt.
signal.signal(signal.SIGINT, on_ctrl_c)

context = zmq.Context()
dealer = context.socket(zmq.DEALER)

# Η ταυτότητα δρομολόγησης ορίζεται ως bytes, πριν από τη σύνδεση.
# Το ROUTER θα τη βλέπει ως πρώτο frame σε κάθε εισερχόμενο μήνυμα.
# Αν παραλείψουμε την επόμενη γραμμή, το ZeroMQ θα δημιουργήσει αυτόματα
# μια ταυτότητα δρομολόγησης, την οποία το ROUTER μπορεί να χρησιμοποιήσει
# κανονικά για να μας στείλει μηνύματα.
# Η αυτόματη ταυτότητα είναι δυαδική: στο ROUTER την εμφανίζουμε με
# {identity!r} και όχι με {identity.decode()}.
dealer.identity = name.encode()

dealer.connect("tcp://localhost:5555")

# Dictionary εκκρεμών μηνυμάτων: transaction_id -> dictionary πεδίων.
# Παράδειγμα: {"T1": {"type": "PREPARE", "client_id": "C1", "amount": 100}}.
# Επαναχρησιμοποίηση του ίδιου κλειδιού θα αντικαθιστούσε την προηγούμενη τιμή.
pending = {}

# Πρώτη επικοινωνία: το ROUTER μαθαίνει την ταυτότητα και τη σύνδεσή μας.
# Το DEALER στέλνει μόνο το περιεχόμενο, χωρίς identity ή κενό frame.
dealer.send_string("HELLO " + name)

print(f"{name}: περιμένω μηνύματα.")
print("Πατήστε Ctrl+C αφού αποθηκευτούν και τα τρία μηνύματα.")

while not reply_now:
    # Αναμονή έως 500 ms για εισερχόμενο μήνυμα
    # Αν υπάρχει μήνυμα, επιστρέφει αμέσως μη μηδενική τιμή, αλλιώς 0.
    # Το timeout επιτρέπει τακτική επιστροφή στην Python και έλεγχο της σημαίας,
    # ακόμη και όταν δεν φτάνουν άλλα μηνύματα.
    if dealer.poll(500):
        message = dealer.recv_string()

        # Tokenization: "PREPARE T1 C1 100" χωρίζεται σε τέσσερα πεδία.
        # Το ποσό μετατρέπεται από string σε ακέραιο πριν αποθηκευτεί.
        msg_type, transaction_id, client_id, amount = message.split()
        pending[transaction_id] = {
            "type": msg_type,
            "client_id": client_id,
            "amount": int(amount)
        }
        print(
            f"{name}: αποθηκεύτηκε {transaction_id}: {pending[transaction_id]}"
            f" | pending = {list(pending)}"
        )

# Μετά το Ctrl+C, απαντάμε μόνο στα μηνύματα που έχουν ήδη αποθηκευτεί.
print(f"{name}: αποστολή {len(pending)} απαντήσεων.")

# list(pending) δίνει τα κλειδιά με τη σειρά εισαγωγής.
# reversed(...) αντιστρέφει εσκεμμένα τη σειρά: T3, T2, T1.
# Η αντιστοίχιση απάντησης-αιτήματος γίνεται από το transaction_id,
# όχι από τη σειρά με την οποία παραλαμβάνονται οι απαντήσεις.
for transaction_id in reversed(list(pending)):
    # Ανάκτηση της εγγραφής και πρόσβαση στα πεδία του εσωτερικού dictionary.
    transaction = pending[transaction_id]
    print(
        f"{name}: απάντηση για {transaction_id}, "
        f"client={transaction['client_id']}, amount={transaction['amount']}"
    )

    # Το transaction_id αρκεί για την αντιστοίχιση με το αρχικό αίτημα.
    reply = f"PREPARED {transaction_id}"
    dealer.send_string(reply)
    print(f"{name}: στάλθηκε {reply}")

# Κλείσιμο της υποδοχής και του context. 
dealer.close()
context.term()

print(f"{name}: τερματισμός.")
