#!/usr/bin/env python3
"""CLI entry point. Standard Python launches Blender, which supplies bpy/NumPy."""
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def blender_path(explicit):
    candidates=[explicit,os.environ.get('BLENDER_BIN'),shutil.which('blender'),
                '/Applications/Blender.app/Contents/MacOS/Blender']
    for item in candidates:
        if item and Path(item).is_file():return str(Path(item).resolve())
    raise ValueError('Blender was not found. Supply --blender /path/to/blender.')


def main():
    parser=argparse.ArgumentParser(description='Generate a swept-letter nameplate with a right-hand display platform.')
    sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('build',help='Create a new, verified nameplate in an empty output directory.')
    build.add_argument('--config',help='JSON object: rows, output, font, length, angle, fit, spacing, steps, views, cache_dir.')
    build.add_argument('--text',help='One text row, preserving capitalization.')
    build.add_argument('--top');build.add_argument('--bottom')
    build.add_argument('--output');build.add_argument('--length',type=float,default=150)
    build.add_argument('--angle',type=float,default=70)
    build.add_argument('--spacing',type=float,default=1.08)
    build.add_argument('--fit',choices=['stretch','preserve'],default='stretch')
    build.add_argument('--steps',type=int,default=96)
    build.add_argument('--views',default='beauty,side,top')
    build.add_argument('--no-render',action='store_true')
    prep=sub.add_parser('preprocess',help='Cache only missing glyphs for a font.')
    prep.add_argument('--chars',default='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
    prep.add_argument('--all-supported',action='store_true')
    for p in (build,prep):
        p.add_argument('--font',default=str(ROOT/'assets/fonts/bandosa.regular.ttf'))
        p.add_argument('--cache-dir')
        p.add_argument('--blender')
    args=parser.parse_args()
    config=vars(args).copy()
    config['bundled_cache']=str(ROOT/'assets/font-cache')
    if args.command=='build':
        if args.config:
            supplied=json.loads(Path(args.config).read_text())
            if not isinstance(supplied,dict):raise ValueError('Job configuration must be a JSON object.')
            allowed={'rows','output','font','length','angle','fit','spacing','steps','views','cache_dir'}
            unknown=set(supplied)-allowed
            if unknown:raise ValueError(f'Unknown config keys: {sorted(unknown)}')
            config.update(supplied)
        else:
            if args.text is not None:
                if args.top is not None or args.bottom is not None:raise ValueError('Use --text or --top/--bottom.')
                config['rows']=[args.text]
            elif args.top is not None and args.bottom is not None:config['rows']=[args.top,args.bottom]
            else:raise ValueError('Provide --text, both --top and --bottom, or a --config file with rows.')
        rows=config.get('rows')
        if not isinstance(rows,list) or not 1<=len(rows)<=2 or any(not isinstance(s,str) or not s.strip() for s in rows):
            raise ValueError('rows must contain one or two nonempty strings.')
        if any('\n' in s or '\r' in s or '\t' in s for s in rows):raise ValueError('Use separate rows, without embedded line breaks or tabs.')
        if not 0<float(config['length'])<=1000:raise ValueError('Length must be in (0, 1000] millimeters.')
        if not 45<=float(config['angle'])<=85:raise ValueError('Supported sweep angles are 45–85 degrees above the base.')
        if config['fit'] not in ('stretch','preserve'):raise ValueError('fit must be stretch or preserve.')
        if not .5<=float(config['spacing'])<=3:raise ValueError('spacing must be between 0.5 and 3.')
        if not 32<=int(config['steps'])<=192:raise ValueError('steps must be between 32 and 192.')
        for key in ('length','angle','spacing'):config[key]=float(config[key])
        config['steps']=int(config['steps'])
        views=config['views'].split(',') if isinstance(config['views'],str) else config['views']
        if not isinstance(views,list):raise ValueError('views must be a list or comma-separated string.')
        config['views']=[] if args.no_render else views
        if any(v not in ('beauty','front','side','back','top') for v in config['views']):raise ValueError('Unknown camera view.')
        if not config.get('output'):raise ValueError('An output directory is required.')
        out=Path(config['output']).resolve()
        if out.exists() and any(out.iterdir()):raise ValueError(f'Output directory is not empty; choose a new version directory: {out}')
        config['output']=str(out)
        cache=Path(config['cache_dir']).resolve() if config.get('cache_dir') else out.parent/'.nameplate-font-cache'
    else:
        cache=Path(args.cache_dir).resolve() if args.cache_dir else Path.cwd()/'.nameplate-font-cache'
        config['characters']=args.chars
        out=cache/'preprocess-runs'
    config['font']=str(Path(config['font']).expanduser().resolve())
    if not Path(config['font']).is_file():raise ValueError('The font file does not exist: '+config['font'])
    config['cache_dir']=str(cache)
    blender=blender_path(args.blender)
    out.mkdir(parents=True,exist_ok=True)
    if args.command=='preprocess':
        out=Path(tempfile.mkdtemp(prefix='run-',dir=out))
        config['result']=str(out/'report.json')
    request=out/'request.json';request.write_text(json.dumps(config,indent=2,ensure_ascii=False))
    log=out/'build.log'
    command=[blender,'-b','--factory-startup','--python-exit-code','1','--python',str(ROOT/'scripts/blender_worker.py'),'--',str(request)]
    print('Running Blender. Log: '+str(log),flush=True)
    with log.open('w') as stream:
        result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
    report_path=Path(config['result']) if args.command=='preprocess' else out/'report.json'
    if result.returncode or not report_path.is_file():
        tail='\n'.join(log.read_text(errors='replace').splitlines()[-24:])
        raise RuntimeError(f'Blender failed (exit {result.returncode}); no completed model is claimed.\n{tail}')
    report=json.loads(report_path.read_text())
    if args.command=='build' and report.get('status')!='PASS':raise RuntimeError('Model validation did not pass.')
    print(json.dumps({'output':str(out),'report':str(report_path),'cache':report.get('cache',report),
                      'stl':str(out/'nameplate.stl') if args.command=='build' else None},indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)
