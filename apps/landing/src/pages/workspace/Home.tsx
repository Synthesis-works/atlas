import { useEffect, useState } from 'react';
import { TextFlippingBoard } from '@/components/ui/text-flipping-board';
import { getCurrentUser } from '@/features/auth/services/authService';

export default function Home() {
  const [username, setUsername] = useState('USER');

  useEffect(() => {
    let isMounted = true;
    
    // 1. Try local storage for an instant render
    try {
      const storedUserRaw = localStorage.getItem('atlas_current_user');
      if (storedUserRaw) {
        const storedUser = JSON.parse(storedUserRaw);
        if (storedUser?.username) {
          const displayUsername = storedUser.username.split('@')[0];
          setUsername(displayUsername.toUpperCase());
        }
      }
    } catch (e) {
      // Ignore JSON parse error
    }

    // 2. Fetch from backend to ensure we have it (since login doesn't fetch it)
    getCurrentUser().then((res) => {
      if (isMounted && res.data?.username) {
        const displayUsername = res.data.username.split('@')[0];
        setUsername(displayUsername.toUpperCase());
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const welcomeMessage = `WELCOME ${username}\nTO ATLAS`;

  return (
    <div className="w-full h-[calc(100vh-4rem)] flex justify-center items-center overflow-hidden">
      <div className="flex justify-center items-center w-full max-w-5xl mx-auto scale-110 md:scale-125 lg:scale-150">
        <TextFlippingBoard 
          text={welcomeMessage}
          duration={1.2}
        />
      </div>
    </div>
  );
}
