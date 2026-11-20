---
permalink: /
title: "About me"
author_profile: true
redirect_from:
  - /about/
  - /about.html
---

I am a Professor of Finance at the Faculty of Management, University of Warsaw, where I head the Department of Banking and Institutional Finance. My research focuses on banking, financial intermediation and macroprudential policy, including how regulation and competition affect bank lending, profitability and risk.

{% assign latest_publication = site.publications | where_exp: 'publication', 'publication.working_paper != true' | sort: 'date' | last %}
{% assign latest_project = site.research | sort: 'start_year' | last %}

- **Latest publication** — [{{ latest_publication.title }}]({{ latest_publication.url | relative_url }}) · [All publications]({{ '/publications/' | relative_url }})
- **Latest NCN project** — [{{ latest_project.title }}]({{ latest_project.url | relative_url }}) · [All research projects]({{ '/research/' | relative_url }})

I am Editor-in-Chief of the *Journal of Banking and Financial Economics*. See [Academic Service]({{ '/academic-service/' | relative_url }}) for editorial and university roles.
