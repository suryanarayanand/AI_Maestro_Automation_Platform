import sys

from web.services.generation_service import create_drafts

batch = int(sys.argv[1])
path = f"Uploads/Ready/Anonymous_Premium_Generation_Batch_{batch}.xlsx"
ids, normalization = create_drafts(path, use_ai=True)
print("batch", batch, "drafts", len(ids), "cases", normalization.case_count, "ids", ids)
