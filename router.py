import zmq

# Το παράδειγμα περιμένει ακριβώς δύο διαφορετικούς DEALER και στέλνει
# τρία μηνύματα στον καθέναν. Κάθε DEALER στέλνει ένα μόνο HELLO.
NUM_DEALERS = 3
NUM_MESSAGES = 3

context = zmq.Context()
router = context.socket(zmq.ROUTER)
router.bind("tcp://*:5555")

# Αποθηκεύουμε τις ταυτότητες δρομολόγησης ως bytes, χωρίς decode,
# ώστε να τις χρησιμοποιήσουμε αργότερα στις αποστολές.
dealers = []
while len(dealers) < NUM_DEALERS:
    # Το DEALER στέλνει ένα frame περιεχομένου (π.χ. b"HELLO P0").
    # Το ROUTER προσθέτει κατά τη λήψη ένα frame με την ταυτότητα του αποστολέα.
    # recv_multipart() επιστρέφει ολόκληρο το μήνυμα: [identity, payload].
    identity, payload = router.recv_multipart()

    # decode() μετατρέπει το περιεχόμενο από bytes σε str για την εκτύπωση.
    # flush=True εμφανίζει άμεσα την εκτύπωση χωρίς αναμονή στο buffer εξόδου.
    print(f"Router: {payload.decode()}", flush=True)
    dealers.append(identity)

# Αφού λάβουμε μήνυμα και από τους δύο DEALER, στέλνουμε όλα τα αιτήματα,
# χωρίς να περιμένουμε απάντηση μετά από κάθε αποστολή.
for k in range(1, NUM_MESSAGES + 1):
    transaction_id = f"T{k}"
    client_id = f"C{k}"
    amount = k * 100

    # Μήνυμα τεσσάρων πεδίων: τύπος, συναλλαγή, client και ποσό.
    message = f"PREPARE {transaction_id} {client_id} {amount}"

    for identity in dealers:
        # Αποστολή multipart μηνύματος.
        # Το πρώτο frame επιλέγει τον παραλήπτη. Το ROUTER το αφαιρεί κατά τη
        # δρομολόγηση, οπότε ο DEALER παραλαμβάνει μόνο το περιεχόμενο του message.
        # encode() μετατρέπει το περιεχόμενο σε bytes για το send_multipart().
        router.send_multipart([identity, message.encode()])
        print(f"Router sent to {identity.decode()}: {message}", flush=True)

# Περιμένουμε συνολικά 2 * 3 = 6 απαντήσεις.
# Ο κάθε DEALER απαντά μόνο αφού ο χρήστης πατήσει Ctrl+C στο τερματικό του.
# Η recv_multipart() εδώ μπλοκάρει μέχρι να υπάρχει επόμενο μήνυμα.
for _ in range(NUM_DEALERS * NUM_MESSAGES):
    # Η identity δείχνει ΠΟΙΟΣ απάντησε και το T1/T2/T3 στο payload
    # δείχνει ΣΕ ΠΟΙΟ αίτημα αναφέρεται η απάντηση.
    # Δεν υποθέτουμε σειρά απαντήσεων μεταξύ διαφορετικών DEALER.
    identity, payload = router.recv_multipart()
    print(f"Router received from {identity.decode()}: {payload.decode()}", flush=True)

# Μετά τη λήψη και των έξι απαντήσεων, το script φτάνει στο τέλος και τερματίζει.
