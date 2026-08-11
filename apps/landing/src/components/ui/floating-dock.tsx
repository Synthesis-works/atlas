import { cn } from '@/lib/utils';
import { Layout } from 'lucide-react';
import {
  AnimatePresence,
  MotionValue,
  motion,
  useMotionValue,
  useSpring,
  useTransform,
} from 'framer-motion';
import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';

export const FloatingDock = ({
  items,
  desktopClassName,
  mobileClassName,
  variant = 'solid',
}: {
  items: { title: string; icon: React.ReactNode; href?: string; onClick?: () => void }[];
  desktopClassName?: string;
  mobileClassName?: string;
  /** 'glass' applies the Atlas liquid-glass surface (landing/marketing);
   *  'solid' keeps the default opaque dark surface (workspace). */
  variant?: 'glass' | 'solid';
}) => {
  return (
    <>
      <FloatingDockDesktop items={items} className={desktopClassName} variant={variant} />
      <FloatingDockMobile items={items} className={mobileClassName} variant={variant} />
    </>
  );
};

const FloatingDockMobile = ({
  items,
  className,
  variant = 'solid',
}: {
  items: { title: string; icon: React.ReactNode; href?: string; onClick?: () => void }[];
  className?: string;
  variant?: 'glass' | 'solid';
}) => {
  const [open, setOpen] = useState(false);
  const isGlass = variant === 'glass';
  const itemSurface = isGlass
    ? 'liquid-glass'
    : 'bg-neutral-900 border border-white/10';
  const toggleSurface = isGlass
    ? 'liquid-glass'
    : 'bg-neutral-800 border border-white/10';
  return (
    <div className={cn('relative block md:hidden', className)}>
      <AnimatePresence>
        {open && (
          <motion.div
            layoutId="nav"
            className="absolute inset-x-0 bottom-full mb-2 flex flex-col gap-2"
          >
            {items.map((item, idx) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 10 }}
                animate={{
                  opacity: 1,
                  y: 0,
                }}
                exit={{
                  opacity: 0,
                  y: 10,
                  transition: {
                    delay: idx * 0.05,
                  },
                }}
                transition={{ delay: (items.length - 1 - idx) * 0.05 }}
              >
                {item.href ? (
                  <Link
                    to={item.href}
                    onClick={() => setOpen(false)}
                    className={cn('flex h-10 w-10 items-center justify-center rounded-full', itemSurface)}
                  >
                    <div className="h-4 w-4 text-neutral-300">{item.icon}</div>
                  </Link>
                ) : (
                  <button
                    type="button"
                    onClick={() => { setOpen(false); item.onClick?.(); }}
                    className={cn('flex h-10 w-10 items-center justify-center rounded-full cursor-pointer', itemSurface)}
                  >
                    <div className="h-4 w-4 text-neutral-300">{item.icon}</div>
                  </button>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      <button
        onClick={() => setOpen(!open)}
        className={cn('flex h-10 w-10 items-center justify-center rounded-full cursor-pointer', toggleSurface)}
      >
        <Layout className="h-5 w-5 text-neutral-400" />
      </button>
    </div>
  );
};

const FloatingDockDesktop = ({
  items,
  className,
  variant = 'solid',
}: {
  items: { title: string; icon: React.ReactNode; href?: string; onClick?: () => void }[];
  className?: string;
  variant?: 'glass' | 'solid';
}) => {
  let mouseX = useMotionValue(Infinity);
  const isGlass = variant === 'glass';
  return (
    <motion.div
      onMouseMove={(e) => mouseX.set(e.pageX)}
      onMouseLeave={() => mouseX.set(Infinity)}
      className={cn(
        'mx-auto hidden h-16 items-end gap-4 rounded-2xl px-4 pb-3 md:flex backdrop-blur-md',
        isGlass
          ? 'liquid-glass'
          : 'bg-neutral-950/80 border border-white/10',
        className,
      )}
    >
      {items.map((item) => (
        <IconContainer mouseX={mouseX} key={item.title} variant={variant} {...item} />
      ))}
    </motion.div>
  );
};

function IconContainer({
  mouseX,
  title,
  icon,
  href,
  onClick,
  variant = 'solid',
}: {
  mouseX: MotionValue;
  title: string;
  icon: React.ReactNode;
  href?: string;
  onClick?: () => void;
  variant?: 'glass' | 'solid';
}) {
  const isGlass = variant === 'glass';
  let ref = useRef<HTMLDivElement>(null);

  let distance = useTransform(mouseX, (val) => {
    let bounds = ref.current?.getBoundingClientRect() ?? { x: 0, width: 0 };

    return val - bounds.x - bounds.width / 2;
  });

  let widthTransform = useTransform(distance, [-150, 0, 150], [40, 80, 40]);
  let heightTransform = useTransform(distance, [-150, 0, 150], [40, 80, 40]);

  let widthTransformIcon = useTransform(distance, [-150, 0, 150], [20, 40, 20]);
  let heightTransformIcon = useTransform(
    distance,
    [-150, 0, 150],
    [20, 40, 20],
  );

  let width = useSpring(widthTransform, {
    mass: 0.1,
    stiffness: 150,
    damping: 12,
  });
  let height = useSpring(heightTransform, {
    mass: 0.1,
    stiffness: 150,
    damping: 12,
  });

  let widthIcon = useSpring(widthTransformIcon, {
    mass: 0.1,
    stiffness: 150,
    damping: 12,
  });
  let heightIcon = useSpring(heightTransformIcon, {
    mass: 0.1,
    stiffness: 150,
    damping: 12,
  });

  const [hovered, setHovered] = useState(false);

  const content = (
    <motion.div
      ref={ref}
      style={{ width, height }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={cn(
        'relative flex aspect-square items-center justify-center rounded-full transition-colors',
        isGlass
          ? 'liquid-glass-card bg-white/[0.04] hover:bg-white/[0.07]'
          : 'bg-neutral-900 border border-white/5 hover:border-white/20',
      )}
    >
      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0, y: 10, x: '-50%' }}
            animate={{ opacity: 1, y: 0, x: '-50%' }}
            exit={{ opacity: 0, y: 2, x: '-50%' }}
            className="absolute -top-8 left-1/2 w-fit rounded-md border border-neutral-900 bg-neutral-950 px-2 py-0.5 text-xs whitespace-pre text-white z-50 shadow-lg"
          >
            {title}
          </motion.div>
        )}
      </AnimatePresence>
      <motion.div
        style={{ width: widthIcon, height: heightIcon }}
        className="flex items-center justify-center text-neutral-300"
      >
        {icon}
      </motion.div>
    </motion.div>
  );

  if (href) {
    return <Link to={href}>{content}</Link>;
  }

  return (
    <button type="button" onClick={onClick} className="bg-transparent border-0 p-0">
      {content}
    </button>
  );
}
