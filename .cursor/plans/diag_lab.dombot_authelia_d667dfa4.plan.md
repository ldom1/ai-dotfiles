---
name: Diag lab.dombot Authelia
overview: La redirection vers `https://lab.dombot.tech/authelia/?rd=...` est attendue pour un visiteur non authentifié. Le diagnostic sur `devbox` consiste à vérifier la chaîne Docker Authelia → nginx instance (:8088) → proxy TLS amont, en s’appuyant sur les pièges déjà documentés dans le repo (headers AuthRequest, `authelia_url`, buffering nginx).
todos:
  - id: docker-authelia
    content: "Sur devbox: docker ps / logs Authelia + test curl 127.0.0.1:9091"
    status: completed
  - id: nginx-8088
    content: curl -I :8088 / et /authelia/ + matcher conf nginx déployée au template dombot
    status: completed
  - id: edge-nginx
    content: "Si portail HTML OK mais JS KO: inspecter proxy amont + buffering (PITFALLS #29)"
    status: completed
  - id: auth-request-logs
    content: "Si 500: error.log nginx + logs Authelia auth-request / authelia_url lookup"
    status: completed
isProject: false
---

# Diagnostic `lab.dombot.tech` / Authelia (SSH devbox)

## Comportement attendu (pour ne pas « corriger » la mauvaise chose)

Dans `[instances/dombot/nginx/nginx.conf](instances/dombot/nginx/nginx.conf)`, les blocs protégés appellent `auth_request /internal/authelia/authz` ; en cas de non-session, nginx exécute `@authelia_redirection`, qui renvoie **volontairement** :

```148:151:instances/dombot/nginx/nginx.conf
        location @authelia_redirection {
            internal;
            return 302 https://$host/authelia/?rd=https://$host$request_uri;
        }
```

Donc **« inaccessible »** + URL `/authelia/?rd=...` décrit en réalité souvent : *la redirection fonctionne, mais le portail Authelia ne s’affiche pas / plante / boucle / erreur 5xx après redirection*.

Une vérification rapide depuis l’extérieur : les deux URL renvoient déjà une page HTML type SPA (« You need to enable JavaScript ») — donc la route répond au moins en HTML ; un échec **chargement des bundles JS** ou une erreur **côté submit / session** reste très plausible.

## Pistes alignées sur la doc interne (`[docs/PITFALLS.md](docs/PITFALLS.md)`)


| Symptôme typique                                                                                           | Cause documentée                                                                                            | Où creuser                                                                                                                                                        |
| ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **500** sur tout le lab après auth                                                                         | `auth_request` → Authelia **400** si `X-Original-URL` / `X-Forwarded-Proto` incohérents avec le TLS au bord | Logs nginx + logs Authelia ; conf `location = /internal/authelia/authz` (déjà corrigée dans le template — vérifier **fichier réellement déployé** sur le serveur) |
| **500** + log Authelia *« authelia url lookup failed »*                                                    | Authelia ≥ 4.38+ : `authelia_url` / `session.cookies`                                                       | `configuration.yml` du conteneur + query `auth-request?authelia_url=...` (déjà dans le template ligne 70)                                                         |
| **Page blanche / portail « vide »** : HTML OK, gros JS en échec (`upstream prematurely closed connection`) | Proxy **amont** (VPS) sans buffering adapté, chemins DERP / latence                                         | Fichier edge `**/etc/nginx/sites-enabled/lab.dombot.tech`** (ou équivalent) — directives `proxy_buffering` / tailles de buffers / timeouts (cf. pitfall **#29**)  |
| Conteneur Authelia **down** ou mauvais port                                                                | Rien à l’écoute sur **9091**                                                                                | `docker ps`, `ss -lntp | grep 9091`, logs conteneur                                                                                                               |


## Séquence de diagnostic sur `ssh devbox` (lecture seule sauf reload volontaire)

1. **État Docker**
  - Lister le service Authelia (nom du service peut varier) : `docker ps -a` + `docker compose ps` depuis le répertoire compose du lab.  
  - Si **Exited** / **Restarting** : `docker logs --tail 200 <container_authelia>`.
2. **Port 9091 sur la machine**
  - `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9091/` ou endpoint connu du health si activé.  
  - Si échec de connexion → priorité : remonter le conteneur / mapping ports `9091:9091`.
3. **Nginx instance lab (port 8088)** — conf **effective**
  - `curl -sI http://127.0.0.1:8088/` (sans cookie) : attendre **302** `Location: https://lab.dombot.tech/authelia/?rd=...`.  
  - `curl -sI http://127.0.0.1:8088/authelia/` : doit être **200** (portail), pas 502/504.  
  - Vérifier que le fichier chargé par nginx correspond au template repo (chemins `internal/authelia`, `proxy_pass ...9091`, `X-Forwarded-Proto https` sur `/authelia/`).
4. **AuthRequest** (si 500 sur routes protégées)
  - Regarder `error.log` nginx au moment d’un hit (`auth request unexpected`, upstream 400).  
  - Croiser avec logs Authelia sur `/api/authz/auth-request`.
5. **Proxy TLS amont** (si symptôme « page blanche » ou assets qui ne finissent pas de charger)
  - Inspecter la conf qui fait `proxy_pass` vers `127.0.0.1:8088` (ou socket interne).  
  - Appliquer le correctif buffering/timeouts du pitfall **#29** si les logs montrent des coupures sur gros fichiers.
6. **Cohérence d’URL publique**
  - Dans Authelia : `server.public_portal`, `default_redirection_url`, `session.domain`, et concordance stricte avec `https://lab.dombot.tech` (pas de mélange `http` / autre host).

## Livrable après exécution

- Tableau **symptôme observé** (code HTTP, extrait `curl -I`, extrait log nginx, extrait log Docker) → **cause** → **correctif cible** (fichier : `configuration.yml` Authelia, nginx edge, ou nginx instance 8088).

**Note** : Ce plan ne remplace pas l’exécution SSH ; en mode plan, aucune connexion au serveur n’a été faite. Une fois validé, exécuter la séquence ci-dessus sur `devbox` donne le diagnostic factuel.