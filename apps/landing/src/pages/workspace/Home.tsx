import { TextFlippingBoard } from '@/components/ui/text-flipping-board';
import { useAuth } from '@/features/auth/AuthProvider';

export default function Home() {
  const { user } = useAuth();

  // AuthProvider already confirmed the session via /auth/me, so no local cache
  // or second profile fetch is needed here.
  const displayName = user?.full_name?.trim() || user?.email?.split('@')[0] || 'USER';

  const welcomeMessage = `WELCOME ${displayName.toUpperCase()}\nTO ATLAS`;

  return (
    <div className="w-full h-[calc(100vh-4rem)] flex justify-center items-center overflow-hidden">
      <div className="flex justify-center items-center w-full max-w-5xl mx-auto scale-110 md:scale-125 lg:scale-150">
        <TextFlippingBoard text={welcomeMessage} duration={1.2} />
      </div>
    </div>
  );
}
