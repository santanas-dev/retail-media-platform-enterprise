# `scripts/legacy/` — карантин

Скрипты здесь **не запускаются**. Каждый несёт баннер `QUARANTINED` с причиной.

Они перезаписывали канонический roadmap-XLSX вручную. После canonical cutover
(`RM-GOV-005`) представления roadmap только генерируются:

```
правка docs/product/roadmap.yaml или docs/product/feature-registry.yaml
  -> python3 scripts/ci/roadmap-generate.py
```

`fix_roadmap_qa.py` дополнительно жёстко зашит на путь чужой машины
(`/home/cobalt/...`) и на этой машине не работал бы в любом случае.

Множество скриптов, которым разрешено писать в roadmap-файлы, замкнуто и проверяется
модулем `ssot` гейта `scripts/ci/roadmap-governance-guard.py`.
