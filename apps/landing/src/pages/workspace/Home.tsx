import { useEffect, useState } from 'react';
import { TextFlippingBoard } from '@/components/ui/text-flipping-board';

export default function Home() {
  const [username, setUsername] = useState('USER');

  useEffect(() => {
    const storedUser = localStorage.getItem('atlas_username');
    if (storedUser) {
      setUsername(storedUser.toUpperCase());
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
