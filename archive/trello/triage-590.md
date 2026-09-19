# charts.home serves the base nginx image's stock index.html and 50x.html

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`COPY dist/ /usr/share/nginx/html/` merges into the base layer's docroot rather than replacing it, so `nginx:alpine`'s stock `/index.html` and `/50x.html` still ship — both confirmed 200 on the live https://charts.home.

No functional effect: helm only fetches `/index.yaml` and the absolute tarball URLs. `/` itself answers 404, because `location / { try_files $uri =404; }` bypasses the index directive.

A one-line `RUN rm` in the Charts Dockerfile closes both, whenever that file is next legitimately touched.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/1ZITmHh7/590-chartshome-serves-the-base-nginx-images-stock-indexhtml-and-50xhtml
- **Short URL**: https://trello.com/c/1ZITmHh7

---
*Last Activity: 8/14/2026, 7:11:10 AM*
*Card ID: 6a7ebee221a2c26ec8058001*
