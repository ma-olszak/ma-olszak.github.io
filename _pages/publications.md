---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

<p>{% if site.author.googlescholar %}<a href="{{ site.author.googlescholar }}">Google Scholar</a>{% endif %}{% if site.author.googlescholar and site.author.orcid %} · {% endif %}{% if site.author.orcid %}<a href="{{ site.author.orcid }}">ORCID</a>{% endif %}</p>

{% assign publication_groups = site.publications | group_by: "working_paper" | sort: "name" %}
{% for group in publication_groups %}
{% if group.name == "true" %}
  <h2 id="working-papers">Working papers</h2>
{% else %}
  <h2 id="articles-and-book-chapters">Articles and book chapters</h2>
{% endif %}
{% assign publications = group.items | sort: "date" | reverse %}
{% assign previous_year = "" %}
{% for post in publications %}
  {% assign year = post.date | date: "%Y" %}
  {% if year != previous_year %}
    <h3>{{ year }}</h3>
    {% assign previous_year = year %}
  {% endif %}
  <article class="archive__item">
    <h4 class="archive__item-title"><a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a></h4>
    {% if post.authors %}
      <p>{{ post.authors | join: ", " | escape }} · <em>{{ post.venue | escape }}</em>{% if post.paperurl %} · <a href="{{ post.paperurl }}">{% if post.doi %}DOI{% else %}Article{% endif %}</a>{% endif %}</p>
    {% else %}
      <p>{{ post.citation | escape }}{% if post.paperurl %} · <a href="{{ post.paperurl }}">Article</a>{% endif %}</p>
    {% endif %}
  </article>
{% endfor %}
{% endfor %}
