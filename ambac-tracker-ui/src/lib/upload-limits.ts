/** The largest document the server accepts — `DocumentsSerializer.MAX_FILE_SIZE` in
 *  PartsTracker/Tracker/serializers/dms.py. One limit for every document upload (the
 *  Documents form, Create Revision, Attach Documents on a record), so a file the
 *  server takes is never refused by a stricter dropzone (user decision 2026-10-28). */
export const DOCUMENT_MAX_BYTES = 100 * 1024 * 1024;
export const DOCUMENT_MAX_LABEL = "100 MB";
