"""Curated source-key coverage of the user's 54 Cricket equipment families."""
import argparse
import json
from pathlib import Path


def audit(manifest, registry, *, require_complete=False):
    if registry.get('version') != 1:
        raise ValueError('Unsupported equipment coverage registry')
    requirements = registry.get('requirements', [])
    if len(requirements) != 54 or {r['id'] for r in requirements} != {f'CE{i:02}' for i in range(1,55)}:
        raise ValueError('Coverage must retain all 54 stable requirement IDs')
    products = {product['sourceKey']: product for product in manifest['products']}
    if len(products) != len(manifest['products']):
        raise ValueError('Duplicate source model in manifest')
    rows = []
    for requirement in requirements:
        if requirement.get('minimumModels') != 2 or not requirement.get('label') or not requirement.get('group'):
            raise ValueError('Equipment requirement labels and two-model minimum must be preserved')
        matches = requirement.get('models', [])
        keys = [match['sourceKey'] for match in matches]
        if len(keys) != len(set(keys)):
            raise ValueError('SKU options or repeated models cannot count as different equipment')
        for match in matches:
            model = products.get(match['sourceKey'])
            if model is None or model.get('sport') != 'cricket':
                raise ValueError('Coverage must reference an accepted Cricket source model')
            if match.get('sourceUrl') != model['source']['url']:
                raise ValueError('Coverage evidence must reference the model source URL')
            evidence = match.get('evidence')
            if not isinstance(evidence,str) or not 20 <= len(evidence) <= 2000:
                raise ValueError('Coverage requires explicit curated usage/subtype evidence')
            if model['image'].get('kind') != 'photograph':
                raise ValueError('Equipment coverage requires genuine reviewed photographs')
        count = len(keys)
        rows.append({'id':requirement['id'],'group':requirement['group'],'label':requirement['label'],
                     'models':count,'minimumModels':2,'missingModels':max(0,2-count),'complete':count>=2})
    report = {'complete':all(r['complete'] for r in rows),'requirements':rows,
              'coveredFamilies':sum(r['complete'] for r in rows),'totalFamilies':54,
              'missingModels':sum(r['missingModels'] for r in rows)}
    if require_complete and not report['complete']:
        raise ValueError(f"Equipment coverage incomplete: {report['coveredFamilies']}/54 families")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('registry',type=Path)
    parser.add_argument('--require-complete',action='store_true')
    args=parser.parse_args()
    print(json.dumps(audit(json.loads(args.manifest.read_text()),json.loads(args.registry.read_text()),
                           require_complete=args.require_complete),indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()
