"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE_URL = "http://127.0.0.1:8001";

type DocumentItem = {
  filename: string;
  source_type: string;
  created_at?: string;
};

export default function DocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadDocuments = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(`${API_BASE_URL}/documents`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Impossible de charger les documents.");
        }

        setDocuments(data.documents || []);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Erreur inconnue lors du chargement.",
        );
      } finally {
        setLoading(false);
      }
    };

    loadDocuments();
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-br from-zinc-950 via-slate-950 to-black text-white p-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Documents
            </h1>
            <p className="mt-2 text-sm text-zinc-400">
              Liste des documents actuellement indexés dans Supabase.
            </p>
          </div>

          <button
            onClick={() => router.push("/")}
            className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm text-zinc-200 hover:bg-white/10 transition"
            type="button"
          >
            Retour au chat
          </button>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl p-6 shadow-[0_0_60px_rgba(0,180,255,0.08)]">
          {loading && (
            <p className="text-zinc-400 animate-pulse">
              Chargement des documents...
            </p>
          )}

          {error && (
            <div className="rounded-2xl border border-red-400/20 bg-red-500/10 p-4 text-red-200">
              {error}
            </div>
          )}

          {!loading && !error && documents.length === 0 && (
            <p className="text-zinc-400">Aucun document indexé pour le moment.</p>
          )}

          {!loading && !error && documents.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {documents.map((doc) => (
                <div
                  key={`${doc.filename}-${doc.created_at || ""}`}
                  className="rounded-2xl border border-white/10 bg-black/20 p-5"
                >
                  <p className="text-sm font-semibold text-white leading-6">
                    {doc.filename}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-cyan-200">
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1">
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
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
