from firebase_functions import https_fn
from firebase_admin import firestore, initialize_app
from datetime import datetime

# Initialize Firebase Admin SDK
initialize_app()

# Firestore client
db = firestore.client()

def save_metadata_to_firestore(entity_id, metadata):
    """
    Save metadata to Firestore.
    """
    doc_ref = db.collection("metadata").document(entity_id)
    doc_ref.set(metadata)
    return {"status": "success", "message": f"Metadata saved for {entity_id}"}

@https_fn.on_request()
def save_metadata(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase HTTP function to save metadata to Firestore.
    """
    try:
        # Parse the JSON payload
        data = req.get_json()
        if not data:
            return https_fn.Response(
                {"status": "error", "message": "Invalid request: No JSON payload"},
                status=400
            )

        # Validate the presence of `entity_id` and `metadata`
        entity_id = data.get("entity_id")
        if not entity_id:
            return https_fn.Response(
                {"status": "error", "message": "Invalid request: Missing 'entity_id'"},
                status=400
            )

        metadata = data.get("metadata")
        if not metadata:
            return https_fn.Response(
                {"status": "error", "message": "Invalid request: Missing 'metadata'"},
                status=400
            )

        # Save metadata to Firestore
        result = save_metadata_to_firestore(entity_id, metadata)

        # Return success response
        return https_fn.Response(
            {
                "status": "success",
                "message": f"Metadata saved for {entity_id}",
                "entity_id": entity_id,
                "timestamp": datetime.utcnow().isoformat()  # Add a timestamp
            },
            status=201
        )

    except Exception as e:
        # Return error response
        return https_fn.Response(
            {
                "status": "error",
                "message": f"An error occurred: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            },
            status=500
        )
