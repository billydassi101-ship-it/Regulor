"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE_URL = "http://127.0.0.1:8001";
const ADMIN_TOKEN_KEY = "regulor_admin_token";

type DocumentItem = {
  filename: string;
  source_type: string;
  created_at?: string;
};

export default function AdminPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [sourceType, setSourceType] = useState("internal");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const storedToken = window.localStorage.getItem(ADMIN_TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
      setAuthenticated(true);
      void loadDocuments();
    }
  }, []);

  const loadDocuments = async () => {
    try {
      setLoadingDocs(true);
      setError("");

      const response = await fetch(`${API_BASE_URL}/documents`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Impossible de charger les documents.");
      }

      setDocuments(data.documents || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de chargement.");
    } finally {
      setLoadingDocs(false);
    }
  };

  const login = async () => {
    try {
      setError("");
      setMessage("");

      const response = await fetch(`${API_BASE_URL}/admin/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Authentification admin échouée.");
      }

      window.localStorage.setItem(ADMIN_TOKEN_KEY, data.token);
      setToken(data.token);
      setAuthenticated(true);
      setPassword("");
      setMessage("Authentification réussie.");
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion.");
    }
  };

  const logout = () => {
    window.localStorage.removeItem(ADMIN_TOKEN_KEY);
    setAuthenticated(false);
    setToken("");
    setFiles([]);
    setMessage("Déconnecté.");
  };

  const uploadFiles = async () => {
    if (!files.length) {
      setError("Sélectionne au moins un fichier.");
      return;
    }

    try {
      setUploading(true);
      setError("");
      setMessage("");

      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      formData.append("source_type", sourceType);

      const response = await fetch(`${API_BASE_URL}/admin/upload`, {
        method: "POST",
        headers: {
          "X-Admin-Token": token,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload administrateur échoué.");
      }

      setMessage(
        `Import terminé: ${data.results?.filter((item: { success: boolean }) => item.success).length || 0} fichier(s) traité(s).`,
      );
      setFiles([]);
      await loadDocuments(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur pendant l'upload.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-zinc-950 via-slate-950 to-black text-white p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Admin
            </h1>
            <p className="mt-2 text-sm text-zinc-400">
              Authentifie-toi pour indexer de nouveaux documents directement
              dans Supabase.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => router.push("/")}
              className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm text-zinc-200 hover:bg-white/10 transition"
              type="button"
            >
              Retour au chat
            </button>
            {authenticated && (
              <button
                onClick={logout}
                className="rounded-2xl border border-red-400/20 bg-red-500/10 px-5 py-3 text-sm text-red-200 hover:bg-red-500/20 transition"
                type="button"
              >
                Déconnexion
              </button>
            )}
          </div>
        </div>

        {!authenticated ? (
          <div className="mx-auto max-w-md rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-6">
            <h2 className="text-xl font-semibold">Connexion admin</h2>
            <p className="mt-2 text-sm text-zinc-400">
              Connecte-toi avec ton compte Supabase admin.
            </p>

            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email admin"
              className="mt-5 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 outline-none focus:border-cyan-400/40 transition"
            />

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Mot de passe admin"
              className="mt-3 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 outline-none focus:border-cyan-400/40 transition"
            />

            <button
              onClick={login}
              className="mt-4 w-full rounded-2xl bg-gradient-to-r from-cyan-400 to-blue-500 px-5 py-3 font-semibold text-black hover:scale-[1.01] transition"
              type="button"
            >
              Se connecter
            </button>

            {error && (
              <p className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 p-4 text-sm text-red-200">
                {error}
              </p>
            )}
          </div>
        ) : (
          <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <section className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-6">
              <h2 className="text-xl font-semibold">
                Importer de nouveaux documents
              </h2>
              <p className="mt-2 text-sm text-zinc-400">
                Les fichiers seront automatiquement lus, chunkés, vectorisés et
                ajoutés à Supabase.
              </p>

              <div className="mt-5 space-y-4">
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
                  multiple
                  onChange={(event) => {
                    const selected = Array.from(event.target.files || []);
                    setFiles(selected);
                  }}
                  className="block w-full text-sm text-zinc-300 file:mr-4 file:rounded-2xl file:border-0 file:bg-cyan-500 file:px-4 file:py-2 file:font-semibold file:text-black hover:file:bg-cyan-400"
                />

                <label className="block text-sm text-zinc-400">
                  Type de source
                  <select
                    value={sourceType}
                    onChange={(e) => setSourceType(e.target.value)}
                    className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 outline-none focus:border-cyan-400/40 transition"
                  >
                    <option value="internal">internal</option>
                    <option value="official">official</option>
                    <option value="admin">admin</option>
                  </select>
                </label>

                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={uploadFiles}
                    disabled={uploading || files.length === 0}
                    className="rounded-2xl bg-gradient-to-r from-cyan-400 to-blue-500 px-5 py-3 font-semibold text-black hover:scale-[1.01] transition disabled:opacity-50"
                    type="button"
                  >
                    {uploading ? "Import en cours..." : "Importer et indexer"}
                  </button>
                  <button
                    onClick={() => setFiles([])}
                    className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm text-zinc-200 hover:bg-white/10 transition"
                    type="button"
                  >
                    Vider la sélection
                  </button>
                </div>

                {files.length > 0 && (
                  <div className="rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-4 text-sm text-cyan-100">
                    {files.length} fichier(s) sélectionné(s)
                    <ul className="mt-3 space-y-1 text-xs text-cyan-200/80">
                      {files.map((file) => (
                        <li key={file.name}>{file.name}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {message && (
                  <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                    {message}
                  </div>
                )}

                {error && (
                  <div className="rounded-2xl border border-red-400/20 bg-red-500/10 p-4 text-sm text-red-100">
                    {error}
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold">Documents indexés</h2>
                  <p className="mt-2 text-sm text-zinc-400">
                    {loadingDocs
                      ? "Chargement..."
                      : `${documents.length} document(s) unique(s)`}
                  </p>
                </div>

                <button
                  onClick={() => loadDocuments(token)}
                  className="rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-zinc-200 hover:bg-white/10 transition"
                  type="button"
                >
                  Rafraîchir
                </button>
              </div>

              <div className="mt-5 max-h-[70vh] overflow-y-auto space-y-3">
                {documents.map((doc) => (
                  <div
                    key={`${doc.filename}-${doc.created_at || ""}`}
                    className="rounded-2xl border border-white/10 bg-black/20 p-4"
                  >
                    <p className="text-sm font-semibold text-white leading-6">
                      {doc.filename}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-cyan-200">
                        {doc.source_type}
                      </span>
                      {doc.created_at && (
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-zinc-300">
                          {new Date(doc.created_at).toLocaleString("fr-FR")}
                        </span>
                      )}
                    </div>
                  </div>
                ))}

                {!loadingDocs && documents.length === 0 && (
                  <p className="text-sm text-zinc-400">
                    Aucun document indexé pour le moment.
                  </p>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </main>
  );
}
