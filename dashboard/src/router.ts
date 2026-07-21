import { useEffect, useState } from "react";

// Roteador mínimo por hash — só 2 telas (diagnóstico e notas metodológicas),
// não precisa de uma lib de rotas. Mesmo padrão (hashchange) do
// climate-injustice-index/dashboard/src/router.ts, simplificado (sem params).
export type Route = "diagnostico" | "notas";

function parseHash(): Route {
  return window.location.hash === "#/notas" ? "notas" : "diagnostico";
}

export function useRoute(): [Route, (r: Route) => void] {
  const [route, setRoute] = useState(parseHash());

  useEffect(() => {
    const onHashChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const nav = (r: Route) => {
    window.location.hash = r === "notas" ? "#/notas" : "#/";
  };

  return [route, nav];
}
