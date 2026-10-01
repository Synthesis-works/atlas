import { useEffect, useState } from 'react';
import { TextFlippingBoard } from '@/components/ui/text-flipping-board';

export default function Home() {
  const [username, setUsername] = useState('USER');

  useEffect(() => {
    try {
      const storedUserRaw = localStorage.getItem('atlas_current_user');
      if (storedUserRaw) {
        const storedUser = JSON.parse(storedUserRaw);
        if (storedUser && storedUser.username) {
          // Fall back to the first part of the email if it's an email address
          const displayUsername = storedUser.username.split('@')[0];
          setUsername(displayUsername.toUpperCase());
        }
      }
    } catch (e) {
      // Ignore JSON parse error
    }
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
